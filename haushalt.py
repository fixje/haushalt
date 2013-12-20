#!/usr/bin/env python2
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

import csv
import sys


def balance(rows):
    """
    Erstelle Saldos
    :rows:  iterable bestehend aus Tripeln (p, v, w)
    """
    balance = {}    # dictionary mit Konten aller Beteiligten
    i = 1
    for row in rows:
        try:
            p = row[0].upper().replace(" ", "")
            v = float(eval(row[1].replace(" ", "")))
            w = row[2].upper().replace(" ", "")
            if not p in balance:
                balance[p] = 0.0
            balance[p] += v                 # p hat gezahlt und bekommt
            for c in w:                     # eine Gutschrift
                if not c in balance:
                    balance[c] = 0.0
                balance[c] -= v / len(w)    # vom Konto jedes Begünstigten wird
            i += 1                          # der gleiche Teil abgezogen
        except:
            print >> sys.stderr, "Error in line %d: %s" % (i, row)
            print >> sys.stderr,  sys.exc_info()[1]
            sys.exit(1)
    return balance


def main(filename):
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        bal = balance(reader)
    print "Saldo"
    print "\t", "\t".join(bal.keys())
    print "\t", "========" * len(bal.keys())
    print "\t", "\t".join(["%.2f" % i for i in bal.values()])

    assert sum([b for b in bal.values()]) == 0
    print
    print "Ausgleichszahlungen"
    pos = [k for k, v in bal.items() if v > 0]
    neg = [k for k, v in bal.items() if v < 0]
    for n in neg:
        while bal[n] < 0:
            p = pos.pop()
            if -bal[n] >= bal[p]:
                v = bal[p]
            elif -bal[n] < bal[p]:
                v = -bal[n]
                pos.append(p)
            print "\t%s an %s:\t€ %.2f" % (n, p, v)
            bal[n] += v
            bal[p] -= v


def test():
    rows = [("D", "15.0", "KH"),
            ("K", "2.5 + 2.5", "KH")
            ]
    bal = balance(rows)
    assert bal["D"] == 15.0
    assert bal["H"] == -10.0
    assert bal["K"] == -5
    ## D bekommt von K 5€ und von H 10€
    rows = [("H", "-250.0", "DH"),
            ]
    bal = balance(rows)
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
        print "Running Tests"
        test()
