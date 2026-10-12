import math
from boxes import Boxes, Arg


class DomeSegment(Boxes):
    """Geometrischer Kuppel-Segment-Generator"""

    description = "Generiert Segmente und Rippen für eine geodätische Kuppel"

    def __init__(self) -> None:
        super().__init__()
        
        # Erstellt eine eigene Einstellungskategorie im Web-Interface
        self.arg_group("DomeSettings", "Kuppel Einstellungen")
        
        # Registriert deine Parameter (Ersetzt die alten tkinter-Entry-Felder)
        self.add_arg("radius", "float", 70.0, "Radius R des Körpers (mm)")
        self.add_arg("neck", "int", 8, "N-Eck Wert (reine Ganzzahl)")
        self.add_arg("abstand", "float", 1.5, "Lamellen-Abstand (mm)")
        
        # Hinweis: 'thickness' (Materialstärke) wird von Boxes.py automatisch bereitgestellt!

    def render(self):
        # Parameter aus dem Web-Interface auslesen
        rad = self.radius
        n_eck = self.neck
        l_abstand = self.abstand
        mat = self.thickness  # Nutzt die globale Materialstärke von Boxes.py
        w_slot = mat

        # --- MATHEMATISCHE GRUNDLAGEN ---
        # Höhe des Viertelkreises (Bogenlänge)
        h = (2 * math.pi * rad) / 4

        # Außenradius des N-Ecks
        r_aussen = rad

        # Basisbreite nach Außenradius-Formel
        b = 2 * r_aussen * math.tan(math.pi / n_eck)

        # Schlitzpositionen berechnen
        pos_a = 0.10 * h
        pos_b = h - (0.10 * h) - mat

        # Abwicklung läuft oben korrekt auf 0 zu
        def get_abwicklung_width(y_from_bottom):
            alpha = (y_from_bottom / h) * (math.pi / 2)
            return r_aussen * math.cos(alpha) * math.tan(math.pi / n_eck)

        # =====================================================================
        # FORM 1: ABWICKLUNG (AUSSENKONTUR)
        # =====================================================================
        steps = 90
        points_left_mm = []
        points_right_mm = []

        for i in range(steps + 1):
            curr_y = (h / steps) * i
            half_w = get_abwicklung_width(curr_y)
            points_left_mm.append((b / 2 - half_w, h - curr_y))
            points_right_mm.append((b / 2 + half_w, h - curr_y))

        # Punkte kombinieren, um ein geschlossenes Polygon zu bilden
        all_points_mm = points_left_mm + list(reversed(points_right_mm))

        # Zeichnet die Außenhaut (Polyline schließt sich automatisch)
        self.polyline(*all_points_mm, close=True)

        # --- LAMELLEN & GRAVUREN / INNENSCHNITTE ---
        ly = l_abstand
        lamellen_index = 1

        while ly < h:
            lw = get_abwicklung_width(ly)
            tree_left = b / 2 - lw
            tree_right = b / 2 + lw
            svg_y = h - ly

            in_slot_buffer = False
            for pos in [pos_a, pos_b]:
                if (pos - w_slot / 2 - 2.0) <= ly <= (pos + w_slot / 2 + 2.0):
                    in_slot_buffer = True

            segments = []
            if lamellen_index % 2 == 1:
                x_start = tree_left + 2.0
                x_end = tree_right - 2.0
                if in_slot_buffer:
                    segments.append((x_start, b / 2 - w_slot / 2 - 2.0))
                    segments.append((b / 2 + w_slot / 2 + 2.0, x_end))
                else:
                    segments.append((x_start, x_end))
            else:
                if in_slot_buffer:
                    segments.append((tree_left, b / 2 - w_slot / 2 - 2.0))
                    segments.append((b / 2 + w_slot / 2 + 2.0, tree_right))
                else:
                    segments.append((tree_left, b / 2 - 1.0))
                    segments.append((b / 2 + 1.0, tree_right))

            # Segmente zeichnen (Boxes.py nutzt ctx.line für einfache Linienzüge)
            for x1, x2 in segments:
                if x1 < x2:
                    self.ctx.line(x1, svg_y, x2, svg_y)
                    self.ctx.stroke()

            ly += l_abstand
            lamellen_index += 1

        # --- SCHLITZQUADRATE IN DIE ABWICKLUNG SCHNEIDEN ---
        for pos in [pos_a, pos_b]:
            sx = b / 2 - w_slot / 2
            sy = h - pos - w_slot / 2
            # Platziert ein fertiges quadratisches Loch
            self.rectangularHole(sx, sy, w_slot, w_slot)

        # =====================================================================
        # FORM 2: KREIS-RIPPE
        # =====================================================================
        # Verschiebt den Startpunkt für das nächste Bauteil, damit sie nicht übereinander liegen
        # b + 30mm Sicherheitsabstand in X-Richtung
        self.ctx.translate(b + 30, 0)

        rx_center = rad + mat
        ry_center = rad
        w_zapfen_halb = (w_slot / 2) / rad
        optischer_shift_y = h - rad

        rippe_gesamt_mm = []
        zapfen_intervalle = []

        for pos in [pos_a, pos_b]:
            w_mitte = pos / rad
            w1 = w_mitte - w_zapfen_halb
            w2 = w_mitte + w_zapfen_halb
            zapfen_intervalle.append((w1, w2, w_mitte))

        anzahl_schritte = 300
        j = 0
        while j <= anzahl_schritte:
            winkel = (j / anzahl_schritte) * (math.pi / 2)
            in_interval = None

            for (w1, w2, w_mitte) in zapfen_intervalle:
                if w1 <= winkel <= w2:
                    in_interval = (w1, w2, w_mitte)
                    break

            if in_interval:
                w1, w2, w_mitte = in_interval

                bx1 = rx_center - rad * math.cos(w1)
                by1 = ry_center - rad * math.sin(w1) + optischer_shift_y
                bx2 = rx_center - rad * math.cos(w2)
                by2 = ry_center - rad * math.sin(w2) + optischer_shift_y

                nx = math.cos(w_mitte)
                ny = -math.sin(w_mitte)

                zx1 = bx1 - mat * nx
                zy1 = by1 + mat * ny
                zx2 = bx2 - mat * nx
                zy2 = by2 + mat * ny

                rippe_gesamt_mm.extend([(bx1, by1), (zx1, zy1), (zx2, zy2), (bx2, by2)])
                j = int((w2 / (math.pi / 2)) * anzahl_schritte) + 1
                continue

            # Standard-Kurvenpunkt ohne Zapfen
            cx = rx_center - rad * math.cos(winkel)
            cy = ry_center - rad * math.sin(winkel) + optischer_shift_y
            rippe_gesamt_mm.append((cx, cy))
            j += 1

        # Schließe die Rippenform (Unterkante und Innenseite zurück zum Start)
        # Die Kontur wird hier geschlossen hinab zum Boden geführt
        rippe_gesamt_mm.append((rx_center, ry_center + optischer_shift_y))
        rippe_gesamt_mm.append((rx_center, optischer_shift_y))

        # Zeichne die komplette Kreis-Rippe
        self.polyline(*rippe_gesamt_mm, close=True)
