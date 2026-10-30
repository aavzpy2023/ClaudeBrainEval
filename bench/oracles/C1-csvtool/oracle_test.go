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

func TestOracleCountDataRows(t *testing.T) {
	out, code := oracleRun(t, "name,age\nann,30\nbob,25\ncy,9\n", "count", "-")
	if code != 0 || out != "3\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleCountHeaderOnlyAndEmptyInput(t *testing.T) {
	if out, code := oracleRun(t, "name,age\n", "count", "-"); code != 0 || out != "0\n" {
		t.Errorf("header only: code %d, got %q", code, out)
	}
	if out, code := oracleRun(t, "", "count", "-"); code != 0 || out != "0\n" {
		t.Errorf("empty input: code %d, got %q", code, out)
	}
}

func TestOracleCountHonoursDelimAndQuotedNewlines(t *testing.T) {
	if out, code := oracleRun(t, "a;b\n1;2\n3;4\n", "count", "--delim", ";", "-"); code != 0 || out != "2\n" {
		t.Errorf("delim: code %d, got %q", code, out)
	}
	if out, code := oracleRun(t, "a,b\n\"x\ny\",2\n3,4\n", "count", "-"); code != 0 || out != "2\n" {
		t.Errorf("quoted newline: code %d, got %q", code, out)
	}
}

func TestOracleCountMissingFileFails(t *testing.T) {
	if _, code := oracleRun(t, "", "count", "/no/such/file.csv"); code != 1 {
		t.Errorf("code %d, want 1", code)
	}
}
