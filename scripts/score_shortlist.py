"""Generate the sourced catalog and scored shortlist used by the buying guide."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from audio_scraper.catalog import CatalogEntry, validate_catalog
from audio_scraper.ebay_sold import market_evidence
from audio_scraper.scoring import PricingEvidence, ScoreInputs, score_candidate

ROOT = Path(__file__).resolve().parents[1]

RESEARCH = {
    "Line 6 POD Studio UX2": {
        "release_year": 2008, "msrp": 199.99, "used_low": 32, "used_high": 52, "confidence": .90,
        "windows_status": "Official download selector lists POD Studio UX2 and Windows 11; verify the current driver on the buyer's exact machine because owner reports still describe legacy-driver friction.",
        "notes": "Two XLR mic preamps, +48 V phantom power, instrument inputs, direct/ToneDirect monitoring. Cheap functional bridge, not a modern long-horizon interface.",
        "sources": [
            "https://line6.com/software/index.html?hardware",
            "https://reverb.com/p/line-6-pod-studio-ux2",
            "https://applink.reverb.com/item/90606891-line-6-pod-studio-ux2-usb-audio-interface-2010s-black?show_sold",
            "https://line6.com/data/l/0a060b4ddf5e4bb4c0e1e7d68/application/pdf/POD_Farm_2_Basic_User_Guide.pdf",
        ],
    },
    "Apogee ONE (generation unspecified) bundle": {
        "release_year": 2009, "msrp": 249, "used_low": 50, "used_high": 140, "confidence": .45,
        "windows_status": "Generation-critical: original 2009 ONE is not Windows 10 compatible; later iPad/Mac/PC ONE has a Windows guide. Treat as incompatible until rear label/generation and breakout cable are verified.",
        "notes": "Only one simultaneous mic/instrument input path; the mixed bundle does not solve the preferred two-preamp foundation. Groove/UA/camera mic value depends on exact models and included cables.",
        "sources": [
            "https://knowledge.apogeedigital.com/legacy-products",
            "https://apogeedigital.com/pdf/Windows-ONE-User-Guide-Nov-2017.pdf",
            "https://www.production-expert.com/home-page/2017/10/11/apogee-announce-windows-10-compatibility-for-one-duet-and-quartet-audio-interfaces",
            "https://reverb.com/item/93472448?show_sold=true",
        ],
    },
    "PreSonus Eris 3.5 + Eris Sub 8BT": {
        "release_year": 2023, "msrp": 324.98, "used_low": 150, "used_high": 240, "confidence": .60,
        "windows_status": "Analog monitoring system; no operating-system driver dependency.",
        "notes": "Compact 2.1 system. Official current prices are $114.99 for Eris 3.5 pair and $209.99 for Sub 8BT. Confirm the ad really includes two 3.5 speakers, subwoofer, all power leads, and interconnects.",
        "sources": [
            "https://www.presonus.com/products/eris-35-2nd-gen-pair",
            "https://www.presonus.com/products/eris-sub-8bt",
            "https://applink.reverb.com/item/74443453-presonus-eris-sub-8bt-compact-8-powered-studio-subwoofer-active-sub-w-bluetooth",
        ],
    },
    "Rockville RPG12": {
        "release_year": None, "msrp": 192.45, "used_low": 90, "used_high": 160, "confidence": .50,
        "windows_status": "Analog powered PA speaker; no operating-system driver dependency.",
        "notes": "200 W RMS / 800 W peak single powered PA. Useful for rehearsal/live reinforcement, but one PA box is not a neutral stereo studio-monitor solution.",
        "sources": [
            "https://rockvilleaudio.com/products/rpg12",
            "https://reverb.com/item/2395480-pair-rockville-power-gig-rpg12-12-powered-active-1600-watt-2-way-dj-pa-speakers",
            "https://www.guitarcenter.com/Used/Rockville/PA-Speakers.gc",
        ],
    },
    "Mackie ProFX10v3": {
        "release_year": 2019, "msrp": 269.99, "used_low": 140, "used_high": 230, "confidence": .85,
        "windows_status": "Official product page provides a Windows ASIO driver and documents high-resolution USB recording; verify driver installation and round-trip recording on Windows 11.",
        "notes": "Four Onyx mic preamps, phantom power, direct monitoring, effects, and 2x4 USB I/O. Excellent jam hub; USB records a stereo mix rather than every channel independently.",
        "sources": [
            "https://mackie.com/en/products/mixers/profxv3-series/ProFX10v3.html",
            "https://reverb.com/item/97064142?show_sold=true",
            "https://applink.reverb.com/item/91228900-mackie-profx10v3-10-channel-mixer-used",
        ],
    },
    "AudioThingies MicroMonsta 1": {
        "release_year": 2016, "msrp": 300, "used_low": 275, "used_high": 350, "confidence": .70,
        "windows_status": "Standalone MIDI synth; audio is analog and editor dependence is not required for normal use.",
        "notes": "Compact eight-voice polyphonic desktop synth. Creative and scarce, but requires the Akai controller and does not close the recording/monitoring gap.",
        "sources": [
            "https://www.audiothingies.com/micromonsta/",
            "https://reverb.com/item/82719453-audiothingies-micromonsta",
        ],
    },
    "Elektron Digitone (original)": {
        "release_year": 2018, "msrp": 759, "used_low": 400, "used_high": 500, "confidence": .80,
        "windows_status": "Standalone synth/sequencer with class-specific Elektron software support; analog audio works independently. Test USB/Overbridge only if that workflow matters.",
        "notes": "Eight-voice FM synth with four synth tracks, four MIDI tracks, sequencer and effects. Best self-contained creative instrument in this shortlist, but foundation comes first.",
        "sources": [
            "https://www.elektron.se/support-downloads/digitone",
            "https://macprovideo.com/article/audio-hardware/elektron-releases-759-digitone-polyphonic-digital-synthesizer",
            "https://reverb.com/news/video-the-best-synths-to-buy-this-year",
        ],
    },
    "Roland MS-1 Sampler": {
        "release_year": 1994, "msrp": 650, "used_low": 100, "used_high": 170, "confidence": .75,
        "windows_status": "Standalone 1994 phrase sampler; no modern driver dependency for analog use.",
        "notes": "Characterful lo-fi phrase sampler with short memory and optional PCMCIA expansion. Case adds value; verify pads, recording, memory retention and card slot.",
        "sources": [
            "https://articles.roland.com/a-history-of-roland-samplers/",
            "https://www.soundonsound.com/reviews/roland-ms1",
            "https://reverb.com/item/97301456?show_sold=true",
        ],
    },
    "Roland AIRA TR-8": {
        "release_year": 2014, "msrp": 499, "used_low": 250, "used_high": 400, "confidence": .85,
        "windows_status": "Roland publishes TR-8 driver 1.5.1 for Windows 10/11.",
        "notes": "Strong hands-on 808/909 performer, but this unit has a repaired kick fader, non-working closed-hat decay, and non-original volume knob. Defects overwhelm the modest discount.",
        "sources": [
            "https://www.roland.com/us/products/tr-8/",
            "https://www.roland.com/us/support/by_product/tr-8/updates_drivers/28aa060d-69f8-42c3-9296-220cbda7d653/",
            "https://reverb.com/item/98276886?show_sold=true",
            "https://reverb.com/item/97666464?show_sold=true",
        ],
    },
    "Casio CT-X700": {
        "release_year": 2018, "msrp": 199.99, "used_low": 100, "used_high": 175, "confidence": .80,
        "windows_status": "Class-compliant-style USB-MIDI use is secondary; normal keyboard/audio operation is standalone.",
        "notes": "Modern 61-key touch-sensitive arranger with AiX sounds. Asking price is at/above common used retailer asks and duplicates the Akai keyboard role.",
        "sources": [
            "https://www.casio.com/ca-en/electronic-musical-instruments/product.CT-X700/",
            "https://www.guitarcenter.com/Used/Casio/Used-Casio-CTX700-Digital-Piano-122553781.gc",
            "https://www.guitarcenter.com/Used/Casio/Used-Casio-CT-X700-122352563.gc",
        ],
    },
    "Casio CTK-1000": {
        "release_year": 1993, "msrp": None, "used_low": 100, "used_high": 200, "confidence": .60,
        "windows_status": "Standalone vintage keyboard; MIDI DIN can be used without a model-specific Windows driver.",
        "notes": "Unusual first-generation CTK with editable IXA sounds. $20 is far below sparse collector comps, but test every key, speaker, button, pitch wheel, MIDI and battery compartment.",
        "sources": [
            "https://sonicstate.com/news/2025/02/25/the-weirdest-casio-ctk-1000/",
            "https://reverb.com/item/72443749-casio-ctk-1000-with-adapter",
            "https://reverb.com/item/69332919-casio-ctk-1000",
        ],
    },
    "Makala MK-TE": {
        "release_year": None, "msrp": 249, "used_low": 50, "used_high": 100, "confidence": .45,
        "windows_status": "Acoustic-electric instrument; no driver dependency.",
        "notes": "Very cheap tenor acoustic-electric. Because a ukulele is already owned, buy only for the tenor size/pickup after checking neck, bridge, tuners and output jack.",
        "sources": [
            "https://kalabrand.com/products/mk-te",
            "https://www.ebay.com/p/3049060902",
        ],
    },
}

DIMENSIONS = {
    "Line 6 POD Studio UX2": dict(gap_fit=30, condition=10, compatibility=6, completeness=8, freshness_proximity=9, fun_factor=6, resale_safety=6),
    "Apogee ONE (generation unspecified) bundle": dict(gap_fit=12, condition=8, compatibility=1, completeness=4, freshness_proximity=4, fun_factor=5, resale_safety=7),
    "PreSonus Eris 3.5 + Eris Sub 8BT": dict(gap_fit=25, condition=13, compatibility=10, completeness=7, freshness_proximity=8, fun_factor=8, resale_safety=8),
    "Rockville RPG12": dict(gap_fit=8, condition=12, compatibility=10, completeness=10, freshness_proximity=6, fun_factor=7, resale_safety=4),
    "Mackie ProFX10v3": dict(gap_fit=27, condition=13, compatibility=9, completeness=6, freshness_proximity=6, fun_factor=9, resale_safety=8),
    "AudioThingies MicroMonsta 1": dict(gap_fit=8, condition=11, compatibility=10, completeness=5, freshness_proximity=6, fun_factor=15, resale_safety=8),
    "Elektron Digitone (original)": dict(gap_fit=12, condition=12, compatibility=10, completeness=6, freshness_proximity=5, fun_factor=15, resale_safety=10),
    "Roland MS-1 Sampler": dict(gap_fit=7, condition=10, compatibility=8, completeness=8, freshness_proximity=6, fun_factor=12, resale_safety=7),
    "Roland AIRA TR-8": dict(gap_fit=6, condition=4, compatibility=10, completeness=10, freshness_proximity=8, fun_factor=13, resale_safety=5),
    "Casio CT-X700": dict(gap_fit=4, condition=11, compatibility=8, completeness=4, freshness_proximity=7, fun_factor=7, resale_safety=6),
    "Casio CTK-1000": dict(gap_fit=5, condition=7, compatibility=7, completeness=10, freshness_proximity=5, fun_factor=11, resale_safety=7),
    "Makala MK-TE": dict(gap_fit=2, condition=11, compatibility=10, completeness=7, freshness_proximity=5, fun_factor=5, resale_safety=5),
}


def main() -> None:
    shortlist_path = ROOT / "data" / "normalized" / "shortlist.json"
    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))["shortlist"]
    sold_path = ROOT / "data" / "research" / "ebay_sold_exact_comparisons.json"
    sold_payload = json.loads(sold_path.read_text(encoding="utf-8"))
    sold_market = market_evidence(sold_payload["listings"])
    entries = []
    scored = []
    for item in shortlist:
        identity, listing = item["identification"], item["listing"]
        model = identity["model"]
        research = dict(RESEARCH[model])
        sold = sold_market.get(model)
        if sold:
            research.update(
                used_low=sold["used_low"],
                used_high=sold["used_high"],
                sample_size=sold["sample_size"],
                confidence=min(.95, max(research["confidence"], .55 + .02 * min(int(sold["sample_size"]), 20))),
            )
            research["evidence_file"] = str(sold_path)
        else:
            research["sample_size"] = 0
        entry = CatalogEntry(
            model=model,
            release_year=research["release_year"],
            msrp=research["msrp"],
            used_low=research["used_low"],
            used_high=research["used_high"],
            sources=tuple(research["sources"]),
            windows_status=research["windows_status"],
            compatibility_notes=research["notes"],
        )
        entries.append(entry)
        inputs = ScoreInputs(
            **DIMENSIONS[model],
            asking_price=listing["asking_price"],
            pricing=PricingEvidence(
                used_low=research["used_low"],
                used_high=research["used_high"],
                confidence=research["confidence"],
            ),
            risk_flags=tuple(identity["risk_flags"]),
        )
        result = score_candidate(inputs)
        scored.append({
            "rank": 0,
            "model": model,
            "role": identity["role"],
            "asking_price": listing["asking_price"],
            "listing_url": listing["url"],
            "distance_miles": listing.get("distance_miles"),
            "posted_at": listing.get("posted_at"),
            "risk_flags": identity["risk_flags"],
            "market": {"used_low": research["used_low"], "used_high": research["used_high"], "confidence": research["confidence"], "sample_size": research["sample_size"]},
            "score_inputs": asdict(inputs),
            "score": asdict(result),
            "research_notes": research["notes"],
            "windows_status": research["windows_status"],
            "sources": research["sources"],
        })

    errors = validate_catalog(entries)
    if errors:
        raise SystemExit("catalog validation failed:\n" + "\n".join(errors))
    scored.sort(key=lambda row: (-row["score"]["total"], row["asking_price"]))
    for rank, row in enumerate(scored, 1):
        row["rank"] = rank

    research_dir = ROOT / "data" / "research"
    normalized_dir = ROOT / "data" / "normalized"
    research_dir.mkdir(parents=True, exist_ok=True)
    as_of = datetime.now().astimezone().isoformat()
    (research_dir / "catalog.json").write_text(json.dumps({
        "as_of": as_of,
        "limitations": [
            "Used ranges are the central 20th-80th percentile of conservatively filtered exact-model eBay completed listings; shipping is not included.",
            "Sparse samples remain low-confidence. PreSonus monitor and subwoofer component ranges are combined; incomparable complete bundles are excluded.",
            "Live asking prices are not treated as completed-sale prices.",
        ],
        "entries": [asdict(entry) | {
            "confidence": next(row["market"]["confidence"] for row in scored if row["model"] == entry.model),
            "sample_size": next(row["market"]["sample_size"] for row in scored if row["model"] == entry.model),
            "notes": RESEARCH[entry.model]["notes"],
        } for entry in entries],
    }, indent=2), encoding="utf-8")
    (normalized_dir / "scored_shortlist.json").write_text(json.dumps({
        "as_of": as_of, "scored": scored
    }, indent=2), encoding="utf-8")
    for row in scored:
        print(f"{row['rank']:>2}. {row['score']['total']:>6.2f}  ${row['asking_price']:<6.0f}  {row['model']}")


if __name__ == "__main__":
    main()
