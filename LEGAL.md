# Dati raccolti dagli archivi IRIS: provenienza e condizioni d'uso

L'Osservatorio di A(i)thena (Fondazione Hannah) mostra un elenco di pubblicazioni di filosofia
tratte dagli archivi istituzionali IRIS di alcuni atenei italiani. Questo documento dice come
sono raccolti quei dati e a quali condizioni.

## Come vengono raccolti

- **Solo tramite OAI-PMH.** I dati sono raccolti esclusivamente dagli endpoint OAI-PMH che gli
  archivi espongono pubblicamente per l'interoperabilità con altri servizi (per esempio OpenAIRE).
  Non vengono lette le pagine web degli archivi né usate altre interfacce.
- **Nel rispetto delle indicazioni tecniche.** Prima di ogni raccolta lo script legge il
  `robots.txt` del sito e salta l'archivio se l'endpoint OAI è escluso. Fra una richiesta e
  l'altra attende due secondi e si identifica con un user agent che rimanda a questo repository.
- **Solo per gli atenei verificati.** Un ateneo viene attivato (`"attivo": true` in
  `scripts/iris_atenei.json`) solo dopo aver letto le sue condizioni d'uso dei metadati; il link
  alla policy, una sintesi e la data della verifica sono registrati nello stesso file.

## Che cosa viene conservato

Solo i metadati bibliografici indispensabili al funzionamento dell'Osservatorio:
identificativo del record, titolo, autori, anno, tipo di pubblicazione, rivista o editore, DOI,
settore scientifico-disciplinare, parole chiave indicate dagli autori, link alla scheda originale.

**Non** vengono scaricati né ripubblicati abstract, full text, PDF, allegati o immagini.

## Quanto viene conservato

Non è una copia degli archivi. Vengono tenuti solo i record con un settore disciplinare di
filosofia (PHIL-xx, già M-FIL/xx) pubblicati nell'anno in corso o in quello precedente: una
piccola frazione di ciascun archivio. Il file `data/iris.json` è un dataset derivato, costruito
per l'Osservatorio.

## Uso e attribuzione

- **Non commerciale.** Le policy degli atenei attivi (Milano, Torino) consentono il riuso dei
  metadati per fini non di lucro ed escludono ogni vantaggio economico privato. L'Osservatorio è
  un servizio gratuito, senza pubblicità: se questo cambiasse, la raccolta andrebbe sospesa e le
  condizioni riesaminate.
- **Fonte sempre indicata.** Ogni record conserva l'ateneo di provenienza e il link alla propria
  scheda nell'archivio, e la pagina li mostra. La pagina elenca gli archivi usati con il link
  alle rispettive condizioni d'uso.

## Stato delle verifiche (20 settembre 2026)

| Ateneo | Condizioni sui metadati | Stato |
|---|---|---|
| Milano Statale | [Policy di AIR](https://air.unimi.it/sr/static/Policy_di_AIR.html): riuso libero per fini non di lucro, con dati bibliografici e link alla pagina originale | attivo |
| Torino | [Politiche di IRIS-AperTO](https://iris.unito.it/sr/htm/politiche.html): riuso libero per fini non di lucro | attivo |
| Padova | [Policy accesso aperto](https://wwwassets.unipd.it/sites/default/files/pdf_imported_files/PolicyAccessoAperto_Unipd_rev20251030_0.pdf): OAI-PMH dichiarato, nessuna licenza sui metadati | in attesa di conferma |
| Sapienza | [Policy open access](https://www.uniroma1.it/sites/default/files/field_file_allegati/dr_3489_modifica_policy_open_access_0.pdf): non tratta il riuso dei metadati | in attesa di conferma |
| Bologna | endpoint non verificato | non attivo |

Nessuno dei `robots.txt` controllati (Milano, Sapienza, Padova, Torino) esclude l'endpoint OAI
o riserva la raccolta per text and data mining.

## Richieste di rimozione

Chi gestisce uno degli archivi, o è autore di un record, può chiedere di escludere dati aprendo
una issue in questo repository. L'ateneo viene disattivato e i suoi record rimossi alla raccolta
successiva.

Questo documento descrive le scelte fatte per restare entro le condizioni dichiarate dagli
archivi; non è un parere legale.
