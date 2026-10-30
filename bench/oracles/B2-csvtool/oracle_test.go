package main

import (
	"bytes"
	"strings"
	"testing"
)

func oracleHeadJSON(in string, n int) (string, error) {
	var buf bytes.Buffer
	err := HeadJSON(strings.NewReader(in), &buf, n, ',', false)
	return buf.String(), err
}

func TestOracleHeadJSONIsOneArray(t *testing.T) {
	got, err := oracleHeadJSON("name,age\nann,30\nbob,25\n", 2)
	if err != nil {
		t.Fatal(err)
	}
	want := `[{"name":"ann","age":"30"},{"name":"bob","age":"25"}]` + "\n"
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleHeadJSONRespectsN(t *testing.T) {
	got, _ := oracleHeadJSON("name,age\nann,30\nbob,25\n", 1)
	if want := `[{"name":"ann","age":"30"}]` + "\n"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestOracleHeadJSONEmptyIsEmptyArray(t *testing.T) {
	for _, in := range []string{"name,age\n", "name,age\nann,30\n"} {
		n := 5
		if strings.Count(in, "\n") > 1 {
			n = 0
		}
		got, err := oracleHeadJSON(in, n)
		if err != nil || got != "[]\n" {
			t.Errorf("%q n=%d: got %q, %v", in, n, got, err)
		}
	}
}

func TestOracleHeadJSONShortAndLongRows(t *testing.T) {
	got, err := oracleHeadJSON("a,b\n1\n", 5)
	if err != nil || got != `[{"a":"1","b":null}]`+"\n" {
		t.Errorf("short row: got %q, %v", got, err)
	}
	if _, err := oracleHeadJSON("a,b\n1,2,3\n", 5); err == nil {
		t.Error("a row longer than the header must still be an error")
	}
}
