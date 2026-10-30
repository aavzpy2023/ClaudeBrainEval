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

func TestOracleAutoDelimiter(t *testing.T) {
	for _, tc := range []struct{ name, in string }{
		{"semicolon", "a;b;c\n1;2;3\n4;5;6\n"},
		{"tab", "a\tb\n1\t2\n"},
		{"pipe", "a|b|c\n1|2|3\n"},
		{"comma", "a,b\n1,2\n"},
	} {
		out, code := oracleRun(t, tc.in, "head", "--delim", "auto", "-")
		if code != 0 || out != tc.in {
			t.Errorf("%s: code %d, got %q, want %q", tc.name, code, out, tc.in)
		}
	}
}

func TestOracleAutoDelimiterWorksForSelect(t *testing.T) {
	out, code := oracleRun(t, "a;b;c\n1;2;3\n", "select", "-c", "b", "--delim", "auto", "-")
	if code != 0 || out != "b\n2\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleAutoDelimiterIgnoresQuotedSeparators(t *testing.T) {
	in := "\"x;y;z\",b\n1,2\n"
	out, code := oracleRun(t, in, "head", "--delim", "auto", "-")
	// the only separator outside quotes is the comma, so that is the delimiter and the field stays whole
	if want := "x;y;z,b\n1,2\n"; code != 0 || out != want {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleAutoDelimiterFallsBackToComma(t *testing.T) {
	out, code := oracleRun(t, "single\n1\n", "head", "--delim", "auto", "-")
	if code != 0 || out != "single\n1\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}

func TestOracleExplicitDelimiterIsStillRespected(t *testing.T) {
	out, code := oracleRun(t, "a;b\n1;2\n", "select", "-c", "a;b", "--delim", ",", "-")
	if code != 0 || out != "a;b\n1;2\n" {
		t.Errorf("code %d, got %q", code, out)
	}
}
