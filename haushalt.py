#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Skript zur Haushaltsabrechnung
#
# Eingabeformat: CSV
#   p, v, w
# p = "Wer hat bezahlt"
# v = "Wert"
# w = "Für wen ist es bestimmt"
#
# p: einzelnes Personenkürzel bestehend aus genau einem Zeichen
# w: String bestehend aus Personenkürzeln
# Zeilen, die mit einem Rautezeichen (#) beginnen, werden zwecks Kommentar-
# funktion ignoriert.
#
# Beispiel:
#   D, 20.00, MK
# "D hat für M und K 20€ bezahlt"
#
# Als Wert können auch Summen direkt eingetragen werden
#  D, 20.0 + 15.50, mK
# Leerzeichen sind erlaubt, zwischen Groß- und Kleinschreibung wird bei den
# Buchstabenkürzeln nicht unterschieden
#
# Wie funktioniert's?
# Für jeden Beteiligten wird ein Konto geführt. Ausgaben eines Beteiligten
# werden auf dessen Konto addiert. Ist jemand Begünstigter einer Ausgabe, wird
# der entsprechende Teil von seinem Konto abgezogen.
# Beispiel: D, 20, DK
#   D hat gezahlt. Auf sein Konto werden 20 addiert. D und K sind Begünstigte
#   der getätigten Ausgabe, also wird der Wert zu gleichen Teilen von ihrem
#   Konto subtrahiert. Ds Konto beträgt am Schluss 10 und K hat einen Saldo
#   von -10. Das bedeutet, dass K an D noch 10€ zahlen muss, damit die Konten
#   ausgeglichen sind.
# Hinweis: Einträge, bei denen Begünstigter und Zahlender gleich sind, ergeben
# keinen Sinn: K, 2, K würde auf Ks Konto 2 addieren und gleich wieder abziehen
#
# Metadaten
# Es können auch Metadaten für die Abrechnung in der Eingabedatei stehen. Unter-
# stützt sind:
# * Titel der Abrechnung [!t]:
#   !tTitel der Abrechnung
# * Mapping der Namenskürzel [!m] (JSON), hier für D,M und K:
#   !m{"D": "Daniel", "M": "Markus", "K": "Kurt"}
# * Kommentar für die ganze Abrechnung [!C]
#   !CHier der Kommentar
# Die Metadaten werden u.a. in der HTML Ausgabe benutzt.
#
#
from __future__ import print_function
from collections import defaultdict
from decimal import *
from random import shuffle

import argparse
import codecs
import json
import sys


dsort = lambda i: i[1]


def balance(rows):
    """
    Erstelle Saldos
    :rows:  iterable bestehend aus Tripeln (p, v, w)
    """
    balance = {}    # dictionary mit Konten aller Beteiligten
    whopaid = {}
    transactions = []
    i = 1
    for row in rows:
        try:
            if row is None:                 # Kommentare ignorieren, aber Zeile
                i += 1                      # zaehlen
                continue
            if row[0] == "":                # Leerzeilen ignorieren
                i += 1
                continue

            repl = lambda s: s.upper().replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")

            p = repl(row[0])
            v = Decimal(str(eval(repl(row[1]))))
            w = repl(row[2])
            if len(row) < 4:
                transactions.append((p, v, w))
            else:
                transactions.append((p, v, w, row[3]))
            if not p in balance:
                balance[p] = Decimal('0')
            if not p in whopaid:
                whopaid[p] = Decimal('0')
            balance[p] += v                 # p hat gezahlt und bekommt
            if v > 0:
                whopaid[p] += v
            for c in w:                     # eine Gutschrift
                if not c in balance:
                    balance[c] = Decimal('0')
                balance[c] -= v / Decimal(str(len(w)))    # vom Konto jedes Begünstigten wird
            i += 1                          # der gleiche Teil abgezogen
        except:
            print("Error in line %d: %s" % (i, row), file=sys.stderr)
            print(sys.exc_info()[1], file=sys.stderr)
            sys.exit(1)
    return (balance, whopaid, transactions)


def transfersGreedy(bal):
    result = []
    # Sortieren verhindert kleine Transaktionen
    pos = [k for k, v in sorted(list(bal.items()), key=dsort, reverse=True)
           if v > 0]
    neg = [k for k, v in sorted(list(bal.items()), key=dsort) if v < 0]
    for n in neg:
        while bal[n] < -0.00001:
            p = pos.pop()
            if -bal[n] >= bal[p]:
                v = bal[p]
            elif -bal[n] < bal[p]:
                v = -bal[n]
                pos.append(p)
            result.append((n, p, v))
            bal[n] += v
            bal[p] -= v
    return result


def transfersFairAll(bal):
    result = []
    # alle ausser einer überweisen, dafür jeder nur ein mal
    while len(bal) > 1:
        srt = [k for k, v in sorted(list(bal.items()), key=dsort)]
        pos = srt[-1]
        neg = srt[0]
        v = -bal[neg]
        bal[pos] -= v
        del bal[neg]
        if v > 0:
            result.append((neg, pos, v))
    return result


def transfersRandom(bal):
    result = []
    pos = [k for k, v in list(bal.items()) if v > 0]
    neg = [k for k, v in list(bal.items()) if v < 0]
    shuffle(pos)
    shuffle(neg)
    for n in neg:
        while bal[n] < -0.00001:
            p = pos.pop()
            if -bal[n] >= bal[p]:
                v = bal[p]
            elif -bal[n] < bal[p]:
                v = -bal[n]
                pos.append(p)
            result.append((n, p, v))
            bal[n] += v
            bal[p] -= v
    return result


html_template = u"""<!DOCTYPE html>
<html>
    <head>
        <title>Abrechnung {{ title }}</title>
        <meta charset="utf-8">
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
    </head>
    <body>
    <div class="container">
        <h1>Abrechnung {{ title }}</h1>
        <hr>
        <div class="row">
            <div class="col-sm-12">
                <h2>Transaktionen</h2>
                <p>Folgende Zahlungen liegen der Berechnung zugrunde.
                Bei einem positiven Betrag hat der Gläubiger diesen für alle Schuldner
                vorgestreckt. In der Bilanz wird dieser Betrag für jeden Schuldner zum gleichen
                Teil verrechnet.<br>Bei einem negativen Betrag schuldet der Gläubiger (linke
                Spalte) diesen dem Schuldner (rechte Spalte), die Bezeichnungen sind in dem
                Fall also vertauscht. Dies dient der Vereinfachung und damit die Beträge unter
                'Guthaben' nicht auftauchen.</p>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Gläubiger</th>
                            <th>Betrag €</th>
                            <th>Schuldner</th>
                            <th>Kommentar</th>
                        </tr>
                    </thead>
                    <tbody>
                    {{ transaction_table }}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="row">
            <div class="col-sm-6">
                <h2>Guthaben</h2>
                <p>Wer hat wie viel vorgelegt? Hier sind alle Transaktionen
                von oben zusammengefasst, die einen <i>positiven</i> Wert aufweisen.</p>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Betrag €</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{ credit_table }}
                    </tbody>
                    <tfoot>
                        <tr class="bg-info">
                            <td><strong>Gesamt</strong></td>
                            <td>{{ credit_sum }}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <div class="col-sm-6">
                <h2>Saldo</h2>
                <p>Nach Kumulierung aller Forderungen und Guthaben: Wer hat wie viel Guthaben/Schulden?</p>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Saldo €</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{ balance_table }}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="row">
            <div class="col-sm-12">
                <h2>Ausgleichszahlungen</h2>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Überweisender</th>
                            <th>Begünstigter</th>
                            <th>Betrag €</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{ transfers_table }}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="row">
            <div class="col-sm-12">
                {{ comment_end }}
            </div>
        </div>
    </div>
    </body>
</html>"""


def writeHtml(filename, transactions, paid, bal, transfers, charmap={}, title="", commentEnd=""):
    getname = lambda c: c if charmap.get(c) is None else charmap.get(c)
    transaction_table = ""
    for t in transactions:
        if len(t) == 3:
            p, v, w = t
            transaction_table += u"<tr><td>%s</td><td>%.2f</td><td>%s</td><td></td></tr>" % (getname(p), v,
                    ",".join([getname(k) for k in list(w)]))
        else:
            p, v, w, c = t
            transaction_table += u"<tr><td>%s</td><td>%.2f</td><td>%s</td><td>%s</td></tr>" % (getname(p), v,
                    ",".join([getname(k) for k in list(w)]), c)

    credit_table = "\n".join([u"<tr><td>%4s</td><td>%.2f</td></tr>" % (getname(k), v)
            for (k, v) in sorted(paid.items(), key=dsort, reverse=True) if v > 0])
    credit_sum = u"%.2f" % sum(paid.values())

    balance_table =  "\n".join([u"<tr class=\"%s\"><td>%4s</td><td>%.2f</td></tr>" % ("success" if v > 0 else "danger",
                                                                                   getname(k), v)
                               for (k, v) in sorted(bal.items(), key=dsort, reverse=True)])

    transfers_table = "\n".join([u"<tr><td>%s</td><td>%s</td><td>%.2f</td></tr>" % (getname(n), getname(p), v)
                                    for n, p, v in transfers])

    comment_end = u""
    if len(commentEnd) > 0:
        comment_end = u"<div class=\"alert alert-info\">%s</div></div>" % commentEnd

    with codecs.open(filename, "w", encoding="utf-8") as f:
        f.write(html_template.replace("{{ title }}", title)
                             .replace("{{ transaction_table }}", transaction_table)
                             .replace("{{ credit_table }}", credit_table)
                             .replace("{{ credit_sum }}", credit_sum)
                             .replace("{{ balance_table }}", balance_table)
                             .replace("{{ transfers_table }}", transfers_table)
                             .replace(u"{{ comment_end }}", comment_end))


def main():
    parser = argparse.ArgumentParser(description=u"Haushaltsrechner")
    parser.add_argument("filename", metavar="FILE", type=str, nargs=1,
                        help="Eingabedatei")
    parser.add_argument("--fair", dest="transferAlgorithm",
                        action="store_const", const=transfersFairAll,
                        default=transfersGreedy,
                        help=u"Nutze Algorithmus, sodass jeder (ausser einer) genau eine Ausgleichszahlung vornehmen muss")
    parser.add_argument("--random", dest="transferAlgorithm",
                        action="store_const", const=transfersRandom,
                        default=transfersGreedy,
                        help=u"Ausgleichszahlungen werden zufällig berechnet, sodass nur Schuldner Transaktionen tätigen müssen. Benötigt NumPy.")
    parser.add_argument("--greedy", dest="transferAlgorithm",
                        action="store_const", const=transfersGreedy,
                        default=transfersGreedy,
                        help=u"Standardalgorithmus für Ausgleichszahlungen")
    parser.add_argument("--html", default=None, nargs=1, metavar="FILE",
                        dest="htmlout", help=u"Output zu HTML (optional)")
    args = parser.parse_args()

    charmap = {}
    title = ""
    commentEnd = ""
    with codecs.open(args.filename[0], 'r', encoding="utf-8") as f:
        lines = []
        for r in f:
            if r.startswith("#"):
                lines.append(None)  # None fuer Kommentare
                continue
            elif r.startswith("!m"):
                try:
                    # Kürzel -> voller Name, falls Zeile mit mapping in CSV
                   charmap = json.loads(r[2:])
                except:
                    print("Error parsing mapping '%s'" % r)
                continue
            elif r.startswith("!t"):
                # titel
                title = r[2:]
                continue
            elif r.startswith("!C"):
                # Kommentar am Ende
                commentEnd = r[2:]
                continue
            s = r.split(",")
            lines.append(tuple((c.replace("\t", "").replace("\n", "")
                            .replace("\r", "") for c in s)))
        bal, paid, transactions = balance(lines)
    print("Wer hat wie viel vorgelegt?")
    print("\n".join(["%4s %8.2f" % (k, v) for (k, v)
                     in sorted(paid.items(), key=dsort, reverse=True)]))
    print()
    print("Ausgaben insgesamt: %.2f" % sum(paid.values()))
    print()

    print("Saldo")
    print("\n".join(["%4s %8.2f" % (k, v) for (k, v) in
                     sorted(bal.items(), key=dsort, reverse=True)]))
    print()

    assert sum([b for b in list(bal.values())]) < 0.01  # Gleitkommaschiss
    print("Ausgleichszahlungen")
    if args.transferAlgorithm == transfersRandom:
        try:
            # Ziel: ungefähr gleiche Anzahl Transaktionen für alle Schuldner
            import numpy as np
            possibleTransfers = [transfersRandom(bal.copy())
                                 for r in range(1000)]
            variances = []
            for k, cTrans in enumerate(possibleTransfers):
                cd = defaultdict(lambda: 0)
                # Anzahl Transaktionen pro Schuldner
                for n, p, v in cTrans:
                    cd[n] += 1
                variances.append((k, np.var(cd.values())))
            bestIndex = min(variances, key=dsort)[0]
            bestSolution = possibleTransfers[bestIndex]
        except:
            print("Warning: Cannot find numpy. Falling back to greedy algorithm.")
            bestSolution = transfersGreedy(bal.copy())
    else:
        bestSolution = args.transferAlgorithm(bal.copy())

    for n, p, v in bestSolution:
        print("%4s an %s: %8.2f" % (n, p, v))

    if args.htmlout is not None:
        writeHtml(args.htmlout[0], transactions, paid, bal, bestSolution, charmap, title, commentEnd)


def test():
    rows = [("D", "15.0", "KH"),
            ("K", "2.5 + 2.5", "KH")
            ]
    bal, paid, transactions = balance(rows)
    assert bal["D"] == 15.0
    assert bal["H"] == -10.0
    assert bal["K"] == -5
    ## D bekommt von K 5€ und von H 10€
    rows = [("H", "-250.0", "DH"),
            ]
    bal, paid, transactions = balance(rows)
    assert bal["D"] == 125.0
    assert bal["H"] == -125.0
    ## Zum Beispiel hat H von K 250€ Miete erhalten
    ## Um das auch in die Gesamtabrechnung einzubeziehen, wird es als negativer
    ## Saldo auf Hs Konto verbucht. Weil sich D und H das Geld teilen sind
    ## beide die Begünstigten. Am Schluss muss nun H an D noch 125€ bezahlen


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        print("Running Tests")
        test()
