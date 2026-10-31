package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"testing"
)

var (
	oracleOnce sync.Once
	oracleBin  string
	oracleErr  error
)

func oracleBinary(t *testing.T) string {
	t.Helper()
	oracleOnce.Do(func() {
		dir, err := os.MkdirTemp("", "csvtool-oracle")
		if err != nil {
			oracleErr = err
			return
		}
		oracleBin = filepath.Join(dir, "csvtool")
		if out, err := exec.Command("go", "build", "-o", oracleBin, ".").CombinedOutput(); err != nil {
			oracleErr = &buildError{string(out)}
		}
	})
	if oracleErr != nil {
		t.Fatalf("build: %v", oracleErr)
	}
	return oracleBin
}

type buildError struct{ out string }

func (e *buildError) Error() string { return e.out }

func oracleRun(t *testing.T, stdin string, args ...string) (string, int) {
	t.Helper()
	cmd := exec.Command(oracleBinary(t), args...)
	cmd.Stdin = bytes.NewBufferString(stdin)
	var so bytes.Buffer
	cmd.Stdout = &so
	code := 0
	if err := cmd.Run(); err != nil {
		code = err.(*exec.ExitError).ExitCode()
	}
	return so.String(), code
}

func TestOracleTailLastRows(t *testing.T) {
	out, code := oracleRun(t, "a,b\n1,x\n2,y\n3,z\n4,w\n", "tail", "-n", "2", "-")
	if code != 0 || out != "a,b\n3,z\n4,w\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleTailDefaultMatchesHead(t *testing.T) {
	var in strings.Builder
	in.WriteString("n\n")
	for i := 1; i <= 30; i++ {
		fmt.Fprintf(&in, "%d\n", i)
	}
	head, _ := oracleRun(t, in.String(), "head", "-")
	tail, code := oracleRun(t, in.String(), "tail", "-")
	if code != 0 || strings.Count(tail, "\n") != strings.Count(head, "\n") || !strings.HasSuffix(tail, "30\n") {
		t.Errorf("head default prints %d lines, tail printed %q", strings.Count(head, "\n"), tail)
	}
}

func TestOracleTailFewerRowsThanN(t *testing.T) {
	out, code := oracleRun(t, "a\n1\n2\n", "tail", "-n", "9", "-")
	if code != 0 || out != "a\n1\n2\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleTailHonoursDelim(t *testing.T) {
	out, code := oracleRun(t, "a;b\n1;2\n3;4\n", "tail", "-n", "1", "--delim", ";", "-")
	if code != 0 || out != "a;b\n3;4\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

// A multi-gigabyte file must not be loaded in memory: peak RSS stays small on a 1.5M-row input.
func TestOracleTailDoesNotLoadTheWholeFile(t *testing.T) {
	bin := oracleBinary(t)
	cmd := exec.Command(bin, "tail", "-n", "3", "-")
	pr, pw, _ := os.Pipe()
	cmd.Stdin = pr
	var so bytes.Buffer
	cmd.Stdout = &so
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	pr.Close()
	go func() {
		defer pw.Close()
		fmt.Fprintln(pw, "id,name,value")
		for i := 0; i < 1500000; i++ {
			fmt.Fprintf(pw, "%d,name-%d,%d\n", i, i, i*7)
		}
	}()
	if err := cmd.Wait(); err != nil {
		t.Fatal(err)
	}
	if !strings.HasSuffix(so.String(), "1499999,name-1499999,10499993\n") {
		t.Errorf("unexpected output tail %q", so.String())
	}
	if rss := cmd.ProcessState.SysUsage().(*syscall.Rusage).Maxrss; rss > 60*1024 {
		t.Errorf("peak memory %d KB: the whole file was loaded", rss)
	}
}
