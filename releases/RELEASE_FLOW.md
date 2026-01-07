# Release flow (ZIP-first)

## Zasady stałe
- Każda wersja = nowy ZIP (kompletna uruchamialna wersja).
- Repo zawiera kod + historię zmian.
- GitHub Release zawiera artefakt ZIP.
- Tag = vX.Y.Z
- Nazwa ZIP: AviationCAMO-MRO_vX.Y.Z_<LABEL>.zip
- Tylko jeden aktualny start: `start_and_test.bat` (bez historycznych .bat)
- Jeden changelog: `RELEASE_NOTES.md` (append-only)

## Procedura wydania (manual)
1) Zaktualizuj kod w repo (zmiany funkcjonalne).
2) Upewnij się, że w root jest tylko `start_and_test.bat`.
3) Uruchom lokalnie i potwierdź PASS (UI/API/Keycloak).
4) Dopisz wpis do `RELEASE_NOTES.md` (nowa sekcja na górze lub na dole – ale konsekwentnie).
5) Commit na `main` z message: `vX.Y.Z: <krótki opis>`.
6) Push `main` do GitHub.
7) GitHub Release:
   - tag: `vX.Y.Z` (utwórz jeśli nie istnieje)
   - title: `vX.Y.Z`
   - opis: sekcja z `RELEASE_NOTES.md`
   - załącz ZIP: `AviationCAMO-MRO_vX.Y.Z_*.zip`

## Reguły ZIP
- ZIP nie jest wersjonowany w repo (nie commitujemy ZIP-ów).
- ZIP trafia wyłącznie jako artefakt do GitHub Release.
