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

from __future__ import print_function

import csv
import sys


def balance(rows):
    """
    Erstelle Saldos
    :rows:  iterable bestehend aus Tripeln (p, v, w)
    """
    balance = {}    # dictionary mit Konten aller Beteiligten
    whopaid = {}
    i = 1
    for row in rows:
        try:
            if row == None:                 # Kommentare ignorieren, aber Zeile
                i += 1                      # zaehlen
                continue
            if row[0] == "":                # Leerzeilen ignorieren
                i += 1
                continue

            p = row[0].upper().replace(" ", "")
            v = float(eval(row[1].replace(" ", "")))
            w = row[2].upper().replace(" ", "")
            if not p in balance:
                balance[p] = 0.0
            if not p in whopaid:
                whopaid[p] = 0.0
            balance[p] += v                 # p hat gezahlt und bekommt
            if v > 0:
                whopaid[p] += v
            for c in w:                     # eine Gutschrift
                if not c in balance:
                    balance[c] = 0.0
                balance[c] -= v / len(w)    # vom Konto jedes Begünstigten wird
            i += 1                          # der gleiche Teil abgezogen
        except:
            print("Error in line %d: %s" % (i, row), file=sys.stderr)
            print(sys.exc_info()[1], file=sys.stderr)
            sys.exit(1)
    return (balance, whopaid)


def main(filename):
    with open(filename, 'r') as f:
        lines = []
        for r in f:
            if r.startswith("#"):
                lines.append(None)  # None fuer Kommentare
                continue
            s = r.split(",")
            lines.append(tuple((c.replace(" ", "").replace("\t", "").\
                                replace("\n", "").replace("\r", "")
                                for c in s)))
        bal, paid = balance(lines)
    print("Wer hat wie viel vorgelegt?")
    print("\t", "\t".join(list(paid.keys())))
    print("\t", "========" * len(list(paid.keys())))
    print("\t", "\t".join(["%.2f" % i for i in list(paid.values())]))
    print()
    print("Ausgaben insgesamt: %.2f" % sum(paid.values()))
    print()

    print("Saldo")
    print("\t", "\t".join(list(bal.keys())))
    print("\t", "========" * len(list(bal.keys())))
    print("\t", "\t".join(["%.2f" % i for i in list(bal.values())]))

    assert sum([b for b in list(bal.values())]) < 0.01  # Gleikommaschiss
    print()
    print("Ausgleichszahlungen")
    pos = [k for k, v in list(bal.items()) if v > 0]
    neg = [k for k, v in list(bal.items()) if v < 0]
    for n in neg:
        while bal[n] < -0.00001:
            p = pos.pop()
            if -bal[n] >= bal[p]:
                v = bal[p]
            elif -bal[n] < bal[p]:
                v = -bal[n]
                pos.append(p)
            print("\t%s an %s:\t€ %.2f" % (n, p, v))
            bal[n] += v
            bal[p] -= v


def test():
    rows = [("D", "15.0", "KH"),
            ("K", "2.5 + 2.5", "KH")
            ]
    bal, paid = balance(rows)
    assert bal["D"] == 15.0
    assert bal["H"] == -10.0
    assert bal["K"] == -5
    ## D bekommt von K 5€ und von H 10€
    rows = [("H", "-250.0", "DH"),
            ]
    bal, paid = balance(rows)
    assert bal["D"] == 125.0
    assert bal["H"] == -125.0
    ## Zum Beispiel hat H von K 250€ Miete erhalten
    ## Um das auch in die Gesamtabrechnung einzubeziehen, wird es als negativer
    ## Saldo auf Hs Konto verbucht. Weil sich D und H das Geld teilen sind
    ## beide die Begünstigten. Am Schluss muss nun H an D noch 125€ bezahlen


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Running Tests")
        test()
