param(
  [string]$Dsn = $env:PG_DSN
)

if (-not $Dsn) {
  Write-Error "Set PG_DSN or pass -Dsn."
  exit 1
}

psql $Dsn -f .\sql\001_schema.sql
psql $Dsn -f .\sql\002_indexes.sql
psql $Dsn -f .\sql\003_seed_reference.sql

