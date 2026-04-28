Get-ChildItem -Recurse -File -Filter *.py |
  % {
    $p = $_.FullName
    $t = Get-Content -LiteralPath $p -Raw
    $n = $t `
      -replace 'from\s+cattle_tracker_app\.views\.cattle_views\s+import','from cattle_tracker_app.views import' `
      -replace 'import\s+cattle_tracker_app\.views\.cattle_views\s+as\s+([A-Za-z_][A-Za-z0-9_]*)','import cattle_tracker_app.views as $1'
    if ($n -ne $t) {
      [IO.File]::WriteAllText($p, $n, [Text.UTF8Encoding]::new($false))
      Write-Host "Updated $p"
    }
  }
