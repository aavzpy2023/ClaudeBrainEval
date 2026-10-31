package main

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
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

func TestOracleDistinctFirstSeenOrder(t *testing.T) {
	out, code := oracleRun(t, "name,city\nann,NYC\nbob,LA\ncy,NYC\ndi,\n", "distinct", "-c", "city", "-")
	if code != 0 || out != "NYC\nLA\n\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleDistinctHonoursDelim(t *testing.T) {
	out, code := oracleRun(t, "a;b\n1;x\n2;x\n", "distinct", "--delim", ";", "-c", "b", "-")
	if code != 0 || out != "x\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleDistinctMissingColumnFailsLikeSelect(t *testing.T) {
	_, selCode := oracleRun(t, "a,b\n1,2\n", "select", "-c", "zzz", "-")
	out, code := oracleRun(t, "a,b\n1,2\n", "distinct", "-c", "zzz", "-")
	if out != "" || code != selCode || code != 3 {
		t.Errorf("select exits %d, distinct exits %d with output %q (want 3)", selCode, code, out)
	}
}
