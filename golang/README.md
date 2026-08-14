# golang/ — Go binding

`tempest.go` implements the Go standard library `math/rand/v2.Source`
interface for Tempest v3 (a single `Uint64` method), so it works with
`rand/v2.New`, `rand.Shuffle`, and the other `math/rand/v2` helpers.

`demo_gofakeit.go` runs Tempest as the randomness source of
[gofakeit](https://github.com/brianvoe/gofakeit) (a fake-data
generator) through its official `math/rand/v2.Source` extension point,
with no upstream modification.

```bash
go build ./... && go test ./...
go run demo_gofakeit.go
```
