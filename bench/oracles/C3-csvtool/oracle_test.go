package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestOracleParseContainsCondition(t *testing.T) {
	c, err := ParseCondition("name~an")
	if err != nil || c != (Condition{Col: "name", Op: "~", Val: "an"}) {
		t.Errorf("got %+v, %v", c, err)
	}
}

func oracleFilter(t *testing.T, expr string) string {
	t.Helper()
	c, err := ParseCondition(expr)
	if err != nil {
		t.Fatal(err)
	}
	in := "name,age\nann,30\nbob,25\nanna,31\n"
	var buf bytes.Buffer
	if err := Filter(strings.NewReader(in), &buf, c, ',', false); err != nil {
		t.Fatal(err)
	}
	return buf.String()
}

func TestOracleContainsFiltersBySubstring(t *testing.T) {
	if got, want := oracleFilter(t, "name~an"), "name,age\nann,30\nanna,31\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleContainsIsCaseSensitiveAndMayMatchNothing(t *testing.T) {
	if got, want := oracleFilter(t, "name~AN"), "name,age\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleContainsIsAlwaysATextComparison(t *testing.T) {
	if got, want := oracleFilter(t, "age~3"), "name,age\nann,30\nanna,31\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleOtherOperatorsStillWork(t *testing.T) {
	if got, want := oracleFilter(t, "age>=30"), "name,age\nann,30\nanna,31\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
