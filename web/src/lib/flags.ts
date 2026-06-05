// Per-team flag SVGs. We import only the 48 flags actually in the 2026 field
// (as URLs, via flag-icons' 4x3 set) rather than the whole flag-icons CSS —
// that keeps the build lean: ~48 small SVGs emitted instead of all ~260.
// Keys are the canonical team names used in predictions.json / data/groups.json.
// flagUrl() returns the asset URL, or null for any unmapped name (a TBD/playoff
// placeholder), in which case TeamBadge falls back to neutral initials.
//
// England and Scotland use flag-icons' sub-national codes (gb-eng, gb-sct).

import dz from "flag-icons/flags/4x3/dz.svg?url";
import ar from "flag-icons/flags/4x3/ar.svg?url";
import au from "flag-icons/flags/4x3/au.svg?url";
import at from "flag-icons/flags/4x3/at.svg?url";
import be from "flag-icons/flags/4x3/be.svg?url";
import ba from "flag-icons/flags/4x3/ba.svg?url";
import br from "flag-icons/flags/4x3/br.svg?url";
import ca from "flag-icons/flags/4x3/ca.svg?url";
import cv from "flag-icons/flags/4x3/cv.svg?url";
import co from "flag-icons/flags/4x3/co.svg?url";
import hr from "flag-icons/flags/4x3/hr.svg?url";
import cw from "flag-icons/flags/4x3/cw.svg?url";
import cz from "flag-icons/flags/4x3/cz.svg?url";
import cd from "flag-icons/flags/4x3/cd.svg?url";
import ec from "flag-icons/flags/4x3/ec.svg?url";
import eg from "flag-icons/flags/4x3/eg.svg?url";
import gbEng from "flag-icons/flags/4x3/gb-eng.svg?url";
import fr from "flag-icons/flags/4x3/fr.svg?url";
import de from "flag-icons/flags/4x3/de.svg?url";
import gh from "flag-icons/flags/4x3/gh.svg?url";
import ht from "flag-icons/flags/4x3/ht.svg?url";
import ir from "flag-icons/flags/4x3/ir.svg?url";
import iq from "flag-icons/flags/4x3/iq.svg?url";
import ci from "flag-icons/flags/4x3/ci.svg?url";
import jp from "flag-icons/flags/4x3/jp.svg?url";
import jo from "flag-icons/flags/4x3/jo.svg?url";
import mx from "flag-icons/flags/4x3/mx.svg?url";
import ma from "flag-icons/flags/4x3/ma.svg?url";
import nl from "flag-icons/flags/4x3/nl.svg?url";
import nz from "flag-icons/flags/4x3/nz.svg?url";
import no from "flag-icons/flags/4x3/no.svg?url";
import pa from "flag-icons/flags/4x3/pa.svg?url";
import py from "flag-icons/flags/4x3/py.svg?url";
import pt from "flag-icons/flags/4x3/pt.svg?url";
import qa from "flag-icons/flags/4x3/qa.svg?url";
import sa from "flag-icons/flags/4x3/sa.svg?url";
import gbSct from "flag-icons/flags/4x3/gb-sct.svg?url";
import sn from "flag-icons/flags/4x3/sn.svg?url";
import za from "flag-icons/flags/4x3/za.svg?url";
import kr from "flag-icons/flags/4x3/kr.svg?url";
import es from "flag-icons/flags/4x3/es.svg?url";
import se from "flag-icons/flags/4x3/se.svg?url";
import ch from "flag-icons/flags/4x3/ch.svg?url";
import tn from "flag-icons/flags/4x3/tn.svg?url";
import tr from "flag-icons/flags/4x3/tr.svg?url";
import us from "flag-icons/flags/4x3/us.svg?url";
import uy from "flag-icons/flags/4x3/uy.svg?url";
import uz from "flag-icons/flags/4x3/uz.svg?url";

const FLAG_URLS: Record<string, string> = {
  Algeria: dz,
  Argentina: ar,
  Australia: au,
  Austria: at,
  Belgium: be,
  "Bosnia and Herzegovina": ba,
  Brazil: br,
  Canada: ca,
  "Cape Verde": cv,
  Colombia: co,
  Croatia: hr,
  "Curaçao": cw,
  "Czech Republic": cz,
  "DR Congo": cd,
  Ecuador: ec,
  Egypt: eg,
  England: gbEng,
  France: fr,
  Germany: de,
  Ghana: gh,
  Haiti: ht,
  Iran: ir,
  Iraq: iq,
  "Ivory Coast": ci,
  Japan: jp,
  Jordan: jo,
  Mexico: mx,
  Morocco: ma,
  Netherlands: nl,
  "New Zealand": nz,
  Norway: no,
  Panama: pa,
  Paraguay: py,
  Portugal: pt,
  Qatar: qa,
  "Saudi Arabia": sa,
  Scotland: gbSct,
  Senegal: sn,
  "South Africa": za,
  "South Korea": kr,
  Spain: es,
  Sweden: se,
  Switzerland: ch,
  Tunisia: tn,
  Turkey: tr,
  "United States": us,
  Uruguay: uy,
  Uzbekistan: uz,
};

/** Flag SVG asset URL for a team, or null if we have no flag for that name. */
export function flagUrl(team: string): string | null {
  return FLAG_URLS[team] ?? null;
}
