# Project conventions for Claude

## Teil 1 — Portfolio-Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen. Das ist dieselbe Asymmetrie wie
  bei der verschwundenen Codex-Meldung weiter unten.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

**Was nur beim Release läuft, bricht beim Release.** Am 19.9.2026 scheiterte
der Release-Lauf von `zurich-opendata-mcp` 0.8.0 — und der Fehler stand am
Ende von sechzig Zeilen Docker-Pull:

```
Checking dist/zurich_opendata_mcp-0.8.0-py3-none-any.whl:
InvalidDistribution: Invalid distribution metadata:
'2.5' is not a valid metadata version
```

Im Repo hatte sich nichts geändert. `[build-system] requires` nennt
`hatchling` ohne Obergrenze, `python -m build` holt also beim Release die
jeweils neuste: `hatchling 1.32.3` schreibt `Metadata-Version: 2.5`, wo
`1.31.0` noch `2.4` schrieb. Die tag-gepinnte `pypa/gh-action-pypi-publish`
stand auf `v1.14.1` und bringt twine 6.1.0 mit, die 2.5 nicht kennt.

**Nicht PyPI hat abgelehnt, sondern das Prüfwerkzeug.** Positivkontrolle:
`hatchling 1.32.3` liegt selbst auf PyPI mit genau dieser Metadata-Version,
während andere Pakete im selben Lauf 2.4 zeigen — die Sonde unterscheidet
also. Die richtige Antwort war deshalb, die Action zu heben (`v1.14.2`,
twine 7), **nicht** das Backend zurückzupinnen. Ein Rückpin bindet das Repo
dauerhaft an eine alte Metadaten-Generation, um ein anderswo gelöstes
Problem zu umgehen.

Vier Handgriffe daraus:

- **Wandern zwei Dinge unabhängig und treffen sich nur beim Release, gehört
  ihr Zusammenspiel in einen Check, der öfter läuft als das Release.** Hier
  in den Job, der ohnehin frei auflöst (`fresh-install`), also auf jedem PR
  und wöchentlich. Dieselbe Klasse wie der 0.5.1-Defekt, nur eine Schicht
  weiter aussen: dort das Artefakt, hier das Werkzeug, das es prüft.
- **Ein Release-Lauf benutzt die Workflow-Datei AM TAG.** Eine Korrektur auf
  dem Standard-Branch rettet einen fehlgeschlagenen Lauf nie rückwirkend, und
  «Re-run jobs» wiederholt exakt denselben Fehler. Der Weg ist
  `workflow_dispatch` vom Standard-Branch — falls der Workflow ihn vorhält.
- **Eine gescheiterte Publikation verbraucht die Versionsnummer nicht, eine
  gelungene ist unwiderruflich.** Deshalb vor dem zweiten Anlauf *alle* Jobs
  lesen, nicht nur den gescheiterten. Hier leitete der Registry-Job seine
  Version sonst aus dem Tag-Namen ab und hätte bei einem Branch-Dispatch
  «main» hineingeschrieben; er fing es selbst ab, aber das wusste vorher
  niemand.
- **Ein Log ist erst gelesen, wenn man beim letzten Fehler angekommen ist.**
  Der Image-Pull davor sieht nach Inhalt aus und ist keiner.

**Eine Quelle ist nicht die Quelle.** Nach dem geglückten Neuanlauf meldete
PyPIs JSON-API (`/pypi/<name>/json`) weiterhin die alte Version, während der
Simple-Index (`/simple/<name>/`) Wheel und sdist der neuen bereits führte und
ein `pip install <name>==<neu>` durchlief. Die JSON-API hängt hinter einem
eigenen Cache. Wer nur sie fragt, widerspricht einem Menschen, der recht hat.
Bei einem Widerspruch zwischen zwei Diensten entscheidet der, der die Sache
*tut* — hier die Installation.

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet weiterhin eine
  Reaktion («otherwise it will react with 👍») — am 23.8. kam in sechs Repos
  die Meldung und in keinem die Reaktion. Der Kasten ist keine Quelle.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an. Das heisst aber
  nicht, dass ein Draft gar keinen Codex-Kommentar trägt: Am 20.9.2026 um
  16:54:52 UTC stand auf dem noch als Draft geführten PR #120 eine
  Kontingent-Meldung, knapp vier Minuten vor «ready». Was sie ausgelöst hat,
  ist ungeklärt — dreizehn Sekunden davor lag ein eigener Kommentar, davor
  ein Push; belegt ist keines von beidem. Für den Review bleibt die Aussage
  richtig, für den Kommentarzähler nicht.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben. Und zwar in
  **zwei** Wortlauten, beide am 20.9.2026 auf PR #120 mitgeschrieben, 230
  Sekunden auseinander:

  ```
  16:54:52  You have reached your Codex usage limits.
  16:58:42  You have reached your Codex usage limits for code reviews.
  ```

  Wer auf den vollen Satz prüft, erkennt die kürzere Fassung nicht. Das Muster
  in `check_codex_verdict.py` sitzt auf dem gemeinsamen Teil und greift für
  beide — das war Glück, nicht Absicht, und ist seit dem 20.9. durch
  `tests/fixtures/codex/kontingent_allgemein.json` abgesichert.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** eine Befundlos-Meldung. Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund und die
beiden Ausfallmeldungen — Kontingent wie Environment — sind gewöhnliche
Issue-Kommentare und trennen sich nur im Text. Beim Draft gibt es überhaupt
nichts, weil Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein
Beleg, sondern ein nicht durchgeführter Test.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
alles andere; wer nur eine nimmt, übersieht den Rest. Genau so ist die
Limit-Meldung zuerst durchgerutscht.

**Und `get_reviews` liefert mehr als Reviews.** GitHub verpackt jede Antwort auf
einen Inline-Kommentar als Review-Objekt — auch die von Codex —, und dieses
trägt den **aktuellen Head**, nicht den geprüften Commit. Am 20.9.2026 auf
PR #119 mitgeschrieben: der echte Review um 12:57:36 auf `6dc81d17cc`, um
13:03:12 eine blosse Thread-Antwort auf `b64b96d2`. Wer Bot-Login und
`commit_id` prüft, hält die Antwort für ein Verdikt zum neuen Head. Genau das
tat der Gate dieses Repos, bis es auffiel; gemessen endete er mit Exit 0 auf
einem Commit, den Codex nie gesehen hatte.

Unterscheidbar sind die beiden am Body: ein echtes Review trägt die Überschrift
«Codex Review» und nennt den geprüften Commit im Text, eine Thread-Antwort hat
gar keinen Body. **Der Text schlägt `commit_id`** — er sagt, was geprüft wurde,
`commit_id` bloss, woran der Kommentar hängt.

**Die Environment-Meldung kann auch anderswo stehen — und anderes heissen.** Im
selben Vorgang kam sie als **Review-Kommentar an einer Datei-Zeile**, nicht als
Issue-Kommentar, wie es oben steht. Und sie kam, während wenige Minuten zuvor ein
GitHub-getriggerter Code-Review derselben PR sauber durchgelaufen war. «Für das
Repo fehlt eine Environment» hiess dort also **nicht** «kein Review möglich»,
sondern betraf offenbar nur das Antworten im Thread. Die vier Gründe oben bleiben
richtig; was nicht stimmt, ist die Annahme, jede Environment-Meldung belege einen
ausgefallenen Review. Bislang eine einzelne Beobachtung — deshalb hier als
Beobachtung notiert und nicht als Regel.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent- **oder** die Environment-Meldung sein — drei
gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen, nicht die Zahl.
Und einen unbekannten vierten Text wörtlich zitieren, statt ihn in eine der
bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon einmal von drei
auf vier Gründe wachsen, und die 👍-Reaktion stand hier zwei Fassungen lang als
Tatsache.

**Seit dem 18.9.2026 kommt eine weitere Textform dazu — und sie ist kein
fünfter Grund, sondern eine Anzeige über den Lauf selbst:**

```
## Codex Review Summary

| Review | Status | Commit | Review trigger |
| --- | --- | --- | --- |
| 📝 Code Review | ✅ Completed <Zeitstempel> | `<sha>` | Draft marked ready |
```

Drei Eigenschaften, die den Umgang mit den vier Gründen oben ändern:

- **Sie ersetzt die bekannten Formen nicht, sie tritt dazu.** Beim befundlosen
  Lauf von `zurich-opendata-mcp` #115 kamen beide: die Tabelle *und* die Zeile
  «Didn't find any major issues». Wer nur eines der beiden sieht, hat nicht
  den anderen Fall vor sich, sondern nur die halbe Antwort.
- **Sie wird in place editiert** — dieselbe `comment_id`, nur `updated_at`
  bewegt sich, während Status, Commit und Trigger wechseln. Ein zweiter
  Review hebt die Kommentarzahl also **nicht**. Das verschärft die Warnung
  oben: Den Text lesen heisst hier, denselben Kommentar erneut zu lesen.
- **Sie nennt den geprüften Commit.** Damit ist erstmals ablesbar, ob der
  Review den aktuellen Head gesehen hat — bisher liess sich das nur hoffen.
  Ein Push löst keinen neuen Review aus; die Trigger sind «open for review»,
  «draft marked ready» und ein `@codex review`-Kommentar. Wer nach dem Review
  noch einen Commit nachschiebt, mergt ihn ungeprüft, solange er nicht von
  Hand nachtriggert.

**Und ein Zustand, der sich von aussen nicht auflösen lässt.** Läuft
der Review auf einem inzwischen **geschlossenen** PR zu Ende, steht die
Tabelle auf `Completed` — aber es kommt weder ein Review-Objekt noch die
Befundlos-Zeile. `get_reviews` leer, `get_review_comments` leer, im
`get_comments` nur die Tabelle. Gemessen an #116 und #117. «Completed» sagt
dann, dass der Lauf fertig ist, nicht wie er ausging: ob es keine Befunde gab
oder ob welche nicht mehr zugestellt werden konnten, ist nicht entscheidbar.
Nicht in eine der bekannten Schubladen zwingen — das ist der Fall, den man
vermeidet, indem man nicht in den laufenden Review hineinmergt.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Codex wird beim Umschalten von Draft auf ready ausgelöst und braucht
danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review nicht
abgewartet. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach
drei bis fünf Sekunden.

Seit es die Summary-Tabelle gibt, ist das **messbar statt vermutet** — sie
nennt Startzeit, Abschlusszeit und den geprüften Commit. Drei Fälle vom
19.9.2026 in `zurich-opendata-mcp`, alle Zeiten UTC:

| PR | ready | gemergt | Review begann | Review fertig | Befundlos-Meldung |
|---|---|---|---|---|---|
| #115 | 18:26:16 | 18:33:27 | 18:30:55 | 18:33:26 | **ja**, Commit genannt |
| #116 | 17:11:25 | 17:11:29 | 17:11:31 | 17:13:42 | nein |
| #117 | 19:21:27 | 19:21:31 | 19:21:33 | 19:24:10 | nein |
| #120 | ~16:58:38 | 16:58:43 | — | — | nein, Kontingent weg |

Bei #116 und #117 begann der Review **nach** dem Merge, um zwei Sekunden, und
lief danach noch gut zwei Minuten auf einem geschlossenen PR. Bei #115 lag
zwischen Befundlos-Meldung und Merge **eine** Sekunde — es ging gut aus, aber
aus Zufall, nicht aus Disziplin.

**#120 ist der teuerste Eintrag dieser Tabelle, weil dort alles vorhanden
war.** Es ist der PR, der den Gate einführte; der Check-Run lief, meldete
korrekt «Kein Verdikt fuer diesen Head» — und der Merge fünf Sekunden nach
«ready» ging trotzdem durch, weil `Codex-Verdikt` zu diesem Zeitpunkt noch
nicht als Required Status Check im Ruleset stand. Genau die Lücke, die zwei
Absätze weiter oben benannt ist, gemessen an dem Vorgang, der sie schliessen
sollte.

Das ist die Pointe des ganzen Abschnitts: Ein Mechanismus, der nur anzeigt,
ändert nichts am Ablauf. Der Haken im Ruleset ist nicht die Kür nach der
Arbeit, er **ist** die Arbeit.

Daraus der Richtwert: der Review braucht **zwei bis drei Minuten** ab «ready».
Und die Erklärung dafür, warum #116 und #117 in genau dem nicht auflösbaren
Zustand landeten, der weiter oben beschrieben ist: ein Review, der auf einem schon
geschlossenen PR fertig wird, hinterlässt nur die Tabelle.

**Und die Folgerung, nachdem es viermal nicht half, das aufzuschreiben.** Diese
Zeilen stehen seit dem 18.9. in diesem Dokument; am 20.9. wurde der PR, der sie
hinzufügte, vier Sekunden nach «ready» gemergt. Ein Text, den man zum
Merge-Zeitpunkt lesen müsste, wird zum Merge-Zeitpunkt nicht gelesen — das ist
keine Nachlässigkeit, sondern eine Eigenschaft des Ablaufs. Wer den Review
wirklich als Gate will, braucht eine Mechanik: einen Check-Run, der rot bleibt,
solange für den aktuellen Head kein Verdikt vorliegt.

Die Entscheidung dafür — *liegt für genau diesen Head ein Verdikt vor?* — steht
in diesem Repo als reine Funktion in `scripts/check_codex_verdict.py`, der
Check-Run dazu in `.github/workflows/codex-gate.yml` (Details zu beidem in
Teil 2). Zum Portieren genügt, beide Dateien zu kopieren.

Der Workflow kam bewusst erst nach dem Skript und in sechs einzelnen Commits.
Der erste Entwurf bündelte beides und lief durch elf Review-Runden; **acht
Befunde betrafen ausschliesslich den Workflow und keiner das Skript** —
Fork-Token, Dependabot, Checkout-Ref, Concurrency, Zustandsführung des
Check-Runs, Job-Status. Fünf davon hatten dieselbe Wurzel: Eine Eigenschaft
eines GitHub-Triggers war auf einen anderen übertragen worden, ohne sie dort
zu messen. Gebündelt liess sich keine davon mehr einzeln belegen.

Das ist die übertragbare Lehre, nicht der Gate: **Eine reine Funktion und die
Plattformweichen drumherum sind zwei verschiedene Arten von Arbeit.** Die erste
lässt sich gegen Aufzeichnungen prüfen, die zweite nur gegen die Plattform
selbst. Sie in einen PR zu legen heisst, den geprüften Teil so lange
festzuhalten, wie der ungeprüfte braucht.

**Und selbst jetzt blockiert er nichts.** Erst als Required Status Check in
einem Ruleset hält er einen Merge auf, und das ist eine Repo-Einstellung, die
kein PR setzen kann. Wer die Dateien kopiert und den Haken vergisst, hat eine
hübschere Anzeige und dieselbe Lücke.

**Ein neuer Workflow ist nicht auf jedem seiner Trigger prüfbar — und welche
stillbleiben, ist nicht zu raten.** `pull_request_target` und `issue_comment`
benutzen nicht die Datei des PR, sondern die des Basis- bzw. Default-Branch.
Liegt sie dort noch nicht, entsteht **gar kein Lauf** — kein übersprungener,
keiner. Am 20.9.2026 über die gesamte Laufhistorie von `codex-gate.yml`
gezählt, als die Datei nur auf dem Branch von PR #120 lag:

| Trigger | Läufe |
|---|---|
| `pull_request` | 17 |
| `pull_request_review` | 17 |
| `pull_request_target` | **0** |
| `issue_comment` | **0** |

Die beiden oberen sind die Positivkontrolle: Dieselbe Datei erzeugte 34 Läufe,
sie ist also gültig und registriert; ein Fehlen ist damit eine Messung und
nicht bloss eine Abwesenheit. `pull_request_review` liest die Fassung des PR —
das ist der Punkt, an dem eine pauschale Regel «alles ausser `pull_request`
nimmt den Default-Branch» falsch wäre. Auf PR #120 fielen Basis- und
Default-Branch zusammen; welcher der beiden für `issue_comment` gilt, trennt
diese Messung nicht.

Der Anlass war ein Ausbleiben: Um 16:54:52 UTC kam die Kontingent-Meldung von
Codex als Issue-Kommentar, und drei Minuten später gab es dazu keinen Lauf.

**Die Gegenprobe kam eine Stunde später von selbst.** Nach dem Merge von
#120 lag die Datei auf `main`; der erste PR danach (#121, Head `2e61bb2`,
17:05:41) erzeugte prompt einen `pull_request_target`-Lauf — vorher null,
nachher einer, ohne dass sich an der Datei etwas geändert hätte. Damit ist
die Erklärung belegt und nicht bloss plausibel.

Dasselbe gilt fürs Ändern eines bestehenden solchen Zweigs: Geprüft wird die
alte Fassung. Das ist die Klasse «Ein Release-Lauf benutzt die Workflow-Datei
AM TAG» weiter unten, nur unauffälliger, weil hier nichts scheitert. Wer das
nicht weiss, hält die Abwesenheit eines Laufs für «der Filter hat gegriffen» —
und genau diesen Fehlschluss habe ich hier zuerst gemacht, in der anderen
Richtung: Ich hielt die Sache für auf `pull_request_target` beschränkt und
zählte `issue_comment` nicht dazu.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — Dieses Repo

**ruff: eine Quelle.** `pyproject.toml` `[dev]` pinnt `ruff==0.16.3`, `uv.lock`
hält dieselbe Version. `ci.yml` rief ruff vorher per
`uv run --with ruff==0.16.1` auf, während der Lock auf `0.15.18` stand — das
überschrieb nur diesen einen Aufruf, und wer lokal `uv run ruff check` fuhr,
lintete mit 0.15.18 gegen ein Gate, das 0.16.1 fuhr. Beim Anheben:
`pyproject.toml` ändern, `uv lock`, `ruff format`, alles zusammen committen.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Kein `.pre-commit-config.yaml`.** Es gibt also keinen zweiten Ort, an dem
eine abweichende ruff-Version stehen könnte — aber auch nichts, das die Gates
vor dem Commit erzwingt. `scripts/check_ruff_pin.py` schützt den Pin nur, wenn
es aufgerufen wird: lokal von Hand, sonst erst in der CI auf dem PR.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```
uv sync --extra dev
uv run python scripts/check_ruff_pin.py
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy
uv run pytest
python scripts/check_version_sync.py
```

`uv run pytest` ist mehr, als dasteht: `addopts` in `pyproject.toml` trägt
`-m 'not live'` **und** `--cov-fail-under=100`. Der Marker-Ausschluss steht
also nicht im Befehl, und ein Lauf über eine einzelne Testdatei fällt am
Coverage-Gate statt am Test.

**`ci.yml` hat keinen `push`-Trigger** — nur `pull_request`, `schedule`,
`workflow_dispatch`. Ein Push direkt auf `main` löst hier nichts aus; was
grün ist, wurde es auf einem PR. Der Job `check` trägt zusätzlich
`if: github.event_name == 'pull_request'`, im Wochenlauf laufen also nur
`fresh-install` und `audit`. Ein grüner Montagslauf sagt nichts über die
Suite oben.

Dritter Job: **`audit`** (pip-audit) — mit `continue-on-error: true` und
damit kein Gate. Rot heisst dort «Advisory anschauen», nicht «Merge
blockiert»; required ist die `check`-Matrix. Beide Matrizen setzen
`fail-fast: false`, Actions sind SHA-gepinnt.

Dazu ein zweiter Job «Fresh-resolve install smoke»: Wheel in ein leeres venv
ohne Lockfile und mit kaltem Cache, dann ein echter MCP-Handshake über
`scripts/smoke_installed.py`. Der Lockfile-Lauf oben kann nicht bemerken, wenn
eine Abhängigkeitsspanne für Fremde kaputt auflöst; dieser Job kann es.

**`scripts/check_codex_verdict.py` — die Entscheidung, noch ohne Workflow.**
Eine reine Funktion: Sie bekommt `head_sha`, `labels`, `comments` und `reviews`
in GitHub-REST-Form und beantwortet eine einzige Frage — liegt für GENAU diesen
Head ein Codex-Verdikt vor? Nicht, ob es gut ist; einen Befund zu beantworten
bleibt Menschenarbeit.

| Beobachtung | zählt als Verdikt? |
|---|---|
| Review-Objekt **mit Body** «Codex Review» auf dem aktuellen Head | ja |
| «Didn't find any major issues» mit passendem Commit | ja |
| Thread-Antwort von Codex (Review-Objekt ohne Body) | nein |
| Summary-Tabelle `Completed`, sonst nichts | nein |
| Summary-Tabelle `Running` | nein |
| Kontingent- oder Environment-Meldung | nein |

Die dritte Zeile ist der teuerste Einzelbefund: Ohne sie zählte eine blosse
Thread-Antwort als Verdikt zum neuen Head (siehe Teil 1). Ausfallmeldungen
entscheiden nichts mehr, sondern werden gesammelt und nur angehängt — sonst
wäre nach einem erschöpften Kontingent nie wieder ein Verdikt erreichbar.
Notausgang ist das Label aus `--waiver-label` (Vorgabe `codex-review-waived`);
es lässt durch und schreibt das in die Begründung.

Geprüft in `tests/test_codex_gate.py` gegen aufgezeichnete Ereignisse in
`tests/fixtures/codex/`; die dortige `PROVENANCE.md` trennt wörtliche
Mitschriften, `CLAUDE.md`-Wortlaute und Konstruiertes.

**Vierter Workflow: `codex-gate.yml`.** Macht aus dem Skript einen Check-Run
`Codex-Verdikt`, der rot bleibt, solange für den aktuellen Head kein Verdikt
vorliegt. Vier Trigger, weil die Verdikte in vier Formen kommen und weil zwei
Token-Sonderfälle einen eigenen Pfad brauchen.

Gemeldet wird über die **Checks-API**, nicht über den Job-Status:
`issue_comment` und `pull_request_review` laufen nicht am Head-SHA, ihr
Job-Status landet also nirgends, wo ein Ruleset ihn sieht.

Die fünf Weichen, je mit dem Befund, der sie erzwungen hat:

| Weiche | Warum |
|---|---|
| `pull_request` nur für dieses Repo | Fork-PRs bekommen dort einen Nur-Lese-Token; der POST endet mit 403, auch für den Notausgang |
| `pull_request_target` für Forks **und Dependabot** | Dependabots Branch liegt in diesem Repo, GitHub stuft den Token trotzdem herunter |
| `ref:` am Checkout gepinnt | Ohne `ref` checkt `pull_request_review` `refs/pull/<n>/merge` aus — Fork-Code, mit `checks: write` |
| Check-Run vorab auf `in_progress` | Sonst bliebe ein älteres Waiver-Grün stehen, wenn ein vorgelagerter Schritt scheitert |
| `concurrency` auf **Job**-Ebene, ohne Abbruch | Auf Workflow-Ebene träte auch der übersprungene Lauf bei; `cancelled` sieht rot aus |

Zwei Dinge, die man dabei leicht falsch herum annimmt. Erstens: «ohne `ref`
bekommt der Job den Basis-Stand» gilt **nur für `pull_request_target`** — am
20.9.2026 an Lauf 35514764426 gemessen, ausgelöst durch
`pull_request_review`:

```
git checkout --force refs/remotes/pull/119/merge
HEAD is now at 18595a4 Merge 601d2214… into a8023ab2…
```

Zweitens: Welcher Trigger zuständig ist und ob der Head vertrauenswürdig ist,
sind **zwei verschiedene Fragen**. Die Abkürzung über `github.event_name` legte
den Gate sofort lahm (Lauf 35515251744: `python: can't open file
'…/scripts/check_codex_verdict.py'`), weil ein `pull_request_review` auf einem
PR aus diesem Repo damit auf der Basis landete, wo das Skript vor dem Merge
nicht liegt. Nur die zweite Frage gehört an den Checkout.

Der **Job-Status hängt nicht am Verdikt** — das Gate ist der Check-Run. Ein
roter Job neben einem grünen Check trägt keine Information, nur Rauschen, und
Rauschen gewöhnt Leute daran, einen roten Eintrag auf diesem PR zu übergehen.
Rot wird der Job nur bei einem Ausfall der Mechanik, und der wird am
Ausgabepräfix des Skripts erkannt, nicht am Exit-Code: «kein Verdikt» und eine
unbehandelte Ausnahme enden beide mit 1.

Fünf Drift-Wachen in `tests/test_codex_gate.py` halten diese Eigenschaften
fest; sie lesen die Datei als Text, weil pyyaml keine Abhängigkeit dieses
Projekts ist.

**Was gemessen ist und was nicht.** Seit dem Merge von PR #120 liegt die
Datei auf `main`, alle vier Trigger sind also scharf. Auf dem PR selbst
konnten sie es nicht sein — `pull_request_target` und `issue_comment` lesen
die Fassung des Basis- bzw. Default-Branch (Teil 1), dort lag nichts.

Gemessen ist damit bisher nur der `pull_request`-Pfad: Head `475fbce9`,
20.9.2026, Check-Run `Codex-Verdikt` auf `failure` («Kein Verdikt fuer diesen
Head») bei gleichzeitig grünem Job `Codex-Verdikt ermitteln` — die
Entkopplung, die auf PR #119 gefehlt hatte. Ein Check-Run, nicht zwei:
`CHECK_ID 106112983618` angelegt und derselbe abgeschlossen, 16:51:57 bis
16:51:59.

**Auf PR #121 kam die Weichenstellung dann gleich zum Vorschein**, Head
`2e61bb2`, 17:05:41 — zwei Läufe für dieselbe Aktion:

| Lauf | Ereignis | Job |
|---|---|---|
| 35524764994 | `pull_request` | `success`, urteilt |
| 35524765030 | `pull_request_target` | **`skipped`** |

Das belegt zwei Annahmen, die bis dahin nur aus der Dokumentation stammten:
`pull_request_target` feuert für **jeden** PR und nicht nur für Forks — die
Prämisse, auf der die `concurrency` auf Job-Ebene beruht —, und der `if`
teilt exklusiv, es handelt genau einer der beiden.

Ungeprüft bleibt damit weniger, aber Wesentliches:

| Weg | Stand |
|---|---|
| `pull_request_target` **feuert und wird übersprungen** | gemessen auf #121 |
| Fork-PR: der privilegierte Zweig **handelt** | offen, bis ein Fork-PR kommt |
| Dependabot: derselbe Zweig | offen, bis zum nächsten Update-PR |
| Grün nach befundloser Meldung (`issue_comment`) | offen, bis ein Codex-Kommentar auf `main`-Basis eintrifft |

Die drei offenen Zeilen decken bis dahin nur die Drift-Wachen und die
Fixtures — also der Text der Datei und aufgezeichnete Antworten, nicht das
Verhalten von GitHub. Beim ersten Dependabot-PR lohnt deshalb der Blick, ob
der Job dort auch wirklich läuft statt übersprungen zu werden.

Der Rest ist gemessen. Auf PR #120, Head `475fbce9`, 20.9.2026: Check-Run
`Codex-Verdikt` auf `failure` («Kein Verdikt fuer diesen Head»), Job
`Codex-Verdikt ermitteln` auf `success` — die Entkopplung, die auf PR #119
gefehlt hatte. Ein Check-Run, nicht zwei: `CHECK_ID 106112983618` wurde
angelegt und derselbe abgeschlossen, 16:51:57 bis 16:51:59.

**Noch nicht scharf, Stand 20.9.2026.** Der Check hält erst auf, wenn er in
einem Ruleset als Required Status Check eingetragen ist. Das ist eine
Repo-Einstellung, die kein PR setzen kann, und solange sie fehlt, ist der
Check eine zutreffende Anzeige und sonst nichts.

Wie wenig das leistet, steht in der Merge-Tabelle in Teil 1: PR #120 wurde
fünf Sekunden nach «ready» gemergt, während der Check korrekt rot meldete.
Der Gate war vollständig, geprüft und wirkungslos.

**Live-Tests: geplanter Workflow vorhanden.** `.github/workflows/live-tests.yml`,
`cron: "43 4 * * 1"` (wöchentlich Mo, 04:43 UTC). `ci.yml` hat zusätzlich einen
eigenen Zeitplan (`17 6 * * 1`). DRIFT-005 ist hier erfüllt — die Live-Suite ist
nicht bloss per Marker ausgeschlossen. `schedule` greift nur auf dem
Default-Branch: Workflow-Änderungen wirken erst nach dem Merge.

`live-tests.yml` pinnt seine Actions per Tag (`@v7`), nicht per SHA — die
SHA-Pins gelten für `ci.yml` und `publish.yml`.

## Changelog discipline

Every code change must include a matching entry in `CHANGELOG.md` under the
`[Unreleased]` block, in the same commit/PR as the change itself.

- Use Keep-a-Changelog sections: `### Added`, `### Changed`, `### Fixed`,
  `### Security`, `### Removed`, `### Deprecated`.
- Pure documentation tweaks, audits, and CI hardening do not need an entry.
  Anything that ships in the wheel does.
- Reference the audit finding ID (`H-1`, `M-3`, …) when fixing one, so the
  changelog tracks back to `audits/zurich-opendata-mcp-audit.md`.
- When cutting a release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
  and add a new empty `[Unreleased]` block at the top.

## Audit follow-ups

All known review backlogs are closed:

- Both audits (`audits/zurich-opendata-mcp-audit.md` and its rerun) shipped
  across PRs #9, #11–#15: H-1 SQL injection, H-2 CQL injection, all Mediums
  and Lows. The M-7 coverage goal is complete — the suite gates at
  `--cov-fail-under=100`.
- The July 2026 solution review (F-1 – F-13) shipped across PRs #40–#54 and
  was released as `0.5.0`: runtime resolution of year-bound UGZ resource
  IDs, shared HTTP client + retries, `zurich_` naming with deprecated STRB
  aliases, `format=json` on every data-bearing tool, SPARQL opt-in flag,
  Literal-typed UGZ filters, ILIKE wildcard escaping (rerun §2.3 — fixed,
  no longer documentation-only), defusedxml, SHA-pinned CI + pip-audit,
  metadata drift guards, and a mypy gate with zero per-module exemptions.

Invariants to preserve in new work: coverage stays at 100%, mypy has no
`ignore_errors` exemptions, doc counts are pinned by drift-guard tests
(update docs and tests together when the tool surface changes), and the
live-marked drift alarms (UGZ yearly resources, UGZ measurement network)
should be run before cutting a release.

Each substantive change should still land as its own PR with a CHANGELOG
entry, referencing the finding ID where one applies.
