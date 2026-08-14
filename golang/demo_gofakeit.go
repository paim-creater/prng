// demo_gofakeit.go — Tempest as the randomness source of gofakeit,
// the de-facto Go fake-data generator (used by trufflehog and many
// others), via the standard math/rand/v2.Source interface.
//
// Scenario: synthetic-data generation for test fixtures / data
// masking — reproducible with a Tempest seed, non-patterned because
// the source is a CSPRNG.
//
// Build (Windows):  go build -o demo_gofakeit.exe demo_gofakeit.go
// Build (Linux):    go build -o demo_gofakeit demo_gofakeit.go
// Run:              ./demo_gofakeit
package main

import (
	"fmt"
	"math/rand/v2"

	gofakeit "github.com/brianvoe/gofakeit/v7"
	"github.com/paim-creater/prng/golang"
)

func main() {
	fmt.Println("Tempest v3 as the source of gofakeit (synthetic data)")
	fmt.Println("====================================================")

	// gofakeit.NewFaker accepts any math/rand/v2.Source — the same
	// interface our Go port implements (KAT-verified bit-exact).
	src := tempest.FromSeed(2026)
	faker := gofakeit.NewFaker(src, true)

	// Reproducible synthetic records with a Tempest seed.
	fmt.Println("\n--- synthetic customer records (seed=2026, run 1) ---")
	first := make([]string, 0, 3)
	for i := 0; i < 3; i++ {
		rec := fmt.Sprintf("%-14s %-12s %-16s %s",
			faker.Person().FirstName, faker.Person().LastName,
			faker.Phone(), faker.Email())
		first = append(first, rec)
		fmt.Println(rec)
	}

	// Same seed -> identical records (reproducibility): fresh faker
	// instances with the same Tempest seed must emit the same stream.
	src2 := tempest.FromSeed(2026)
	faker2 := gofakeit.NewFaker(src2, true)
	fmt.Println("\n--- same seed re-run (must match above) ---")
	ok := true
	for i := 0; i < 3; i++ {
		rec := fmt.Sprintf("%-14s %-12s %-16s %s",
			faker2.Person().FirstName, faker2.Person().LastName,
			faker2.Phone(), faker2.Email())
		if rec != first[i] {
			ok = false
		}
		fmt.Println(rec)
	}
	fmt.Println("\nreproducible with same Tempest seed:", ok)

	// Statistical sanity of the source driving gofakeit.
	src3 := tempest.FromSeed(7)
	r := rand.New(src3)
	sum := 0.0
	for i := 0; i < 1e6; i++ {
		sum += r.Float64()
	}
	fmt.Printf("\n1M Float64 samples: mean = %.5f (expect ~0.5)\n",
		sum/1e6)
	fmt.Println("\nConclusion: gofakeit (a real, widely-used GitHub")
	fmt.Println("library) runs on Tempest via the standard rand.Source")
	fmt.Println("interface - no modification of gofakeit needed.")
}
