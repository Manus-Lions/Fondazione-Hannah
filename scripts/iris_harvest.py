#!/usr/bin/env python3
"""Raccolta delle pubblicazioni di filosofia dagli archivi IRIS degli atenei italiani.

Usa OAI-PMH, il protocollo che gli archivi istituzionali espongono apposta perché
i metadati vengano raccolti da aggregatori (OpenAIRE, BASE, CORE...). Conserva solo
i metadati bibliografici indispensabili all'Osservatorio (identificativo, titolo, autori,
anno, tipo, rivista o editore, DOI, settore disciplinare, parole chiave, link alla scheda
dell'ateneo): niente abstract, full text, PDF o allegati. Vedi LEGAL.md.

Prima di raccogliere da un archivio controlla che il suo robots.txt non escluda /oai;
se lo esclude, l'archivio viene saltato.

Tiene i lavori con un settore scientifico-disciplinare di filosofia
(PHIL-xx, o il vecchio M-FIL/xx) pubblicati nell'anno in corso o in quello precedente.

La raccolta procede per finestre mensili di data di modifica e ricorda fin dove
è arrivata (file di stato): se un'esecuzione finisce il tempo, la successiva riprende.

Uso:  python iris_harvest.py --config iris_atenei.json --out site/data
Solo libreria standard, nessuna dipendenza.
"""
import argparse, datetime as dt, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, urllib.robotparser
import xml.etree.ElementTree as ET

NS = {"oai": "http://www.openarchives.org/OAI/2.0/",
      "dc": "http://purl.org/dc/elements/1.1/",
      "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"}
USER_AGENT = ("AithenaOsservatorio/1.0 (raccolta metadati OAI-PMH per un osservatorio sulla filosofia; "
              "+https://github.com/Manus-Lions/Fondazione-Hannah)")
PAUSA = 2.0                       # secondi fra una richiesta e l'altra, per non pesare sui server
SSD_RE = re.compile(r"^\s*Settore\s+([A-Z]+(?:-[A-Z]+)?[-/ ]?\d+(?:/[A-Z])?)\s*-\s*(.+)$", re.I)
FIL_RE = re.compile(r"^(PHIL-|M-FIL/)", re.I)
TIPI = {"article": "articolo", "book": "monografia", "bookPart": "capitolo",
        "conferenceObject": "atti di convegno", "review": "recensione", "doctoralThesis": "tesi di dottorato",
        "contributionToPeriodical": "contributo in rivista", "editorial": "editoriale", "other": "altro"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fetch(url, tentativi=5):
    attesa = 10
    for i in range(tentativi):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After")
                attesa = int(ra) if ra and ra.isdigit() else attesa
            elif e.code < 500:
                raise
            log(f"    HTTP {e.code}, riprovo fra {attesa}s")
        except Exception as e:  # timeout, connessione chiusa...
            log(f"    {type(e).__name__}: {e}, riprovo fra {attesa}s")
        time.sleep(min(attesa, 300))
        attesa *= 2
    raise RuntimeError(f"nessuna risposta dopo {tentativi} tentativi: {url}")


def testo(el):
    return re.sub(r"\s+", " ", (el.text or "")).strip()


DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+")


def robots_ok(base):
    """True se il robots.txt del sito non vieta al nostro user agent l'endpoint OAI."""
    p = urllib.parse.urlparse(base)
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.parse(fetch(f"{p.scheme}://{p.netloc}/robots.txt", tentativi=2).decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        return e.code in (404, 410)          # nessun robots.txt: nessun divieto
    return rp.can_fetch(USER_AGENT, base + "?verb=ListRecords")


def parse_record(rec, ateneo):
    head = rec.find("oai:header", NS)
    if head is None or head.get("status") == "deleted":
        return None
    dc = rec.find("oai:metadata/oai_dc:dc", NS)
    if dc is None:
        return None
    campo = lambda n: [t for t in (testo(e) for e in dc.findall("dc:" + n, NS)) if t]
    ssd, kw = [], []
    for s in campo("subject"):
        m = SSD_RE.match(s)
        if m:
            ssd.append({"c": m.group(1).upper().replace(" ", ""), "n": m.group(2).strip()})
        else:
            kw += [k.strip(" .;,") for k in re.split(r"[;,]", s) if k.strip(" .;,")]
    if not any(FIL_RE.match(x["c"]) for x in ssd):
        return None
    doi = next((m.group(0).rstrip(".,;") for x in campo("identifier") + campo("relation")
                for m in [DOI_RE.search(x)] if m), None)
    anno = next((int(m.group(0)) for d in campo("date") for m in [re.search(r"\b(19|20)\d{2}\b", d)] if m), None)
    rel = campo("relation")
    rivista = next((r.split(":", 1)[1].strip() for r in rel if r.lower().startswith("journal:")), None)
    tipo = next((t.rsplit("/", 1)[-1] for t in campo("type") if "eu-repo/semantics" in t), None)
    url = next((i for i in campo("identifier") if i.startswith("http")), None)
    autori = list(dict.fromkeys(campo("creator")))
    out = {
        "id": testo(head.find("oai:identifier", NS)),
        "a": ateneo,
        "t": (campo("title") or ["Senza titolo"])[0],
        "au": autori,
        "y": anno,
        "tp": TIPI.get(tipo, tipo),
        "v": rivista or next(iter(campo("publisher")), None),
        "kw": list(dict.fromkeys(kw))[:20],
        "ssd": [x["c"] for x in ssd],
        "doi": doi,
        "u": url,
    }
    return {k: v for k, v in out.items() if v not in (None, [], "")}


def finestre(da, a):
    """Finestre mensili [inizio, fine] di date di modifica."""
    cur = da
    while cur <= a:
        nxt = (cur.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        yield cur, min(nxt - dt.timedelta(days=1), a)
        cur = nxt


def raccogli_finestra(base, inizio, fine, ateneo, scadenza):
    """Tutti i record di filosofia modificati nella finestra. None se il tempo è finito."""
    params = {"verb": "ListRecords", "metadataPrefix": "oai_dc",
              "from": inizio.isoformat(), "until": fine.isoformat()}
    url, trovati, pagine = base + "?" + urllib.parse.urlencode(params), [], 0
    while url:
        if time.time() > scadenza:
            return None
        root = ET.fromstring(fetch(url))
        pagine += 1
        err = root.find("oai:error", NS)
        if err is not None:
            if err.get("code") == "noRecordsMatch":
                break
            raise RuntimeError(f"errore OAI {err.get('code')}: {testo(err)}")
        lr = root.find("oai:ListRecords", NS)
        for rec in (lr.findall("oai:record", NS) if lr is not None else []):
            r = parse_record(rec, ateneo)
            if r:
                trovati.append(r)
        tok = lr.find("oai:resumptionToken", NS) if lr is not None else None
        url = (base + "?" + urllib.parse.urlencode({"verb": "ListRecords", "resumptionToken": testo(tok)})
               if tok is not None and testo(tok) else None)
        if url:
            time.sleep(PAUSA)
    log(f"    {inizio}…{fine}: {pagine} pagine, {len(trovati)} di filosofia")
    return trovati


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True, help="cartella dove scrivere iris.json e iris-stato.json")
    ap.add_argument("--minuti", type=float, default=300, help="tempo massimo di questa esecuzione")
    args = ap.parse_args()

    conf = json.load(open(args.config, encoding="utf-8"))
    atenei = [a for a in conf["atenei"] if a.get("attivo", True)]
    os.makedirs(args.out, exist_ok=True)
    p_dati, p_stato = os.path.join(args.out, "iris.json"), os.path.join(args.out, "iris-stato.json")
    dati = json.load(open(p_dati, encoding="utf-8")) if os.path.exists(p_dati) else {"records": []}
    stato = json.load(open(p_stato, encoding="utf-8")) if os.path.exists(p_stato) else {}

    oggi = dt.date.today()
    anno_min = oggi.year - 1
    inizio_std = dt.date(anno_min, 1, 1)       # un lavoro del 2025 può essere stato depositato a inizio 2025
    records = {r["id"]: r for r in dati.get("records", []) if (r.get("y") or 0) >= anno_min}
    attivi = {a["id"] for a in atenei}
    records = {k: r for k, r in records.items() if r.get("a") in attivi}   # ateneo disattivato: record rimossi
    for r in records.values():
        r.pop("ab", None)                        # gli abstract non si conservano
    avvio, budget = time.time(), args.minuti * 60
    report = []

    for i, at in enumerate(atenei):
        # ogni ateneo ha una quota equa del tempo che resta
        restanti = len(atenei) - i
        scadenza = time.time() + (budget - (time.time() - avvio)) / restanti
        st = stato.get(at["id"], {})
        fatto = dt.date.fromisoformat(st["fatto_fino_a"]) if st.get("fatto_fino_a") else inizio_std - dt.timedelta(days=1)
        # ripassa sempre l'ultimo giorno già fatto: le modifiche di quel giorno potevano essere incomplete
        da = max(inizio_std, fatto)
        log(f"== {at['nome']} da {da}")
        esito = {"id": at["id"], "nome": at["nome"], "ok": True, "fonte": at["oai"],
                 "condizioni": at.get("condizioni"), "uso": at.get("uso")}
        try:
            if not robots_ok(at["oai"]):
                raise RuntimeError("il robots.txt dell'archivio esclude la raccolta: archivio saltato")
            for a, b in finestre(da, oggi):
                trovati = raccogli_finestra(at["oai"], a, b, at["id"], scadenza)
                if trovati is None:
                    log("    tempo finito, riprendo alla prossima esecuzione")
                    esito["parziale"] = True
                    break
                for r in trovati:
                    if (r.get("y") or 0) >= anno_min:
                        records[r["id"]] = r
                    else:
                        records.pop(r["id"], None)
                stato[at["id"]] = {"fatto_fino_a": b.isoformat()}
                json.dump(stato, open(p_stato, "w", encoding="utf-8"), indent=1)
        except Exception as e:
            log(f"    ERRORE: {e}")
            esito.update(ok=False, errore=str(e)[:300])
        esito["fino_a"] = stato.get(at["id"], {}).get("fatto_fino_a")
        report.append(esito)

    recs = sorted(records.values(), key=lambda r: (-(r.get("y") or 0), r["t"]))
    for e in report:
        e["lavori"] = sum(1 for r in recs if r["a"] == e["id"])
    out = {"generato": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "anni": [anno_min, oggi.year],
           "nota": ("Metadati bibliografici essenziali raccolti via OAI-PMH dagli archivi istituzionali IRIS elencati, "
                    "filtrati sui settori di filosofia e sugli ultimi due anni, per uso non commerciale. "
                    "Ogni record rimanda alla propria scheda originale. Non è una copia degli archivi."),
           "atenei": report, "records": recs}
    tmp = p_dati + ".tmp"
    json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, p_dati)
    log(f"Fatto: {len(recs)} lavori di filosofia da {len(report)} atenei.")


if __name__ == "__main__":
    main()
