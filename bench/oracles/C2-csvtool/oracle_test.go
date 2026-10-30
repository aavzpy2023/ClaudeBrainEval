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

func TestOracleColumnsListsHeaderNames(t *testing.T) {
	out, code := oracleRun(t, "name,age,city\nann,30,NYC\n", "columns", "-")
	if code != 0 || out != "name\nage\ncity\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleColumnsHonoursDelim(t *testing.T) {
	out, code := oracleRun(t, "a;b\n1;2\n", "columns", "--delim", ";", "-")
	if code != 0 || out != "a\nb\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleColumnsEmptyInputPrintsNothing(t *testing.T) {
	out, code := oracleRun(t, "", "columns", "-")
	if code != 0 || out != "" {
		t.Errorf("code %d, got %q", code, out)
	}
}
