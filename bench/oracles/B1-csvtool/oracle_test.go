package main

import (
	"bytes"
	"strings"
	"testing"
)

func oracleStats(t *testing.T, in, col string) string {
	t.Helper()
	var buf bytes.Buffer
	if err := Stats(strings.NewReader(in), &buf, col, ',', false); err != nil {
		t.Fatal(err)
	}
	return buf.String()
}

func TestOracleMeanSkipsEmptyCells(t *testing.T) {
	got := oracleStats(t, "k,v\na,1\nb,\nc,2\nd,3\n", "v")
	if want := "count: 4\nsum: 6\nmean: 2\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleMeanFractional(t *testing.T) {
	got := oracleStats(t, "v\n1\n2\n", "v")
	if want := "count: 2\nsum: 3\nmean: 1.5\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleMeanWithoutNumbers(t *testing.T) {
	got := oracleStats(t, "k,v\na,\nb,\n", "v")
	if want := "count: 2\nsum: 0\nmean: n/a\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleMeanShortRowsCountAsEmpty(t *testing.T) {
	got := oracleStats(t, "a,v\nx,4\ny\nz,6\n", "v")
	if want := "count: 3\nsum: 10\nmean: 5\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
