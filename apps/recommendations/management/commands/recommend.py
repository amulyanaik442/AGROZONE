"""
CLI tool to run a soil recommendation from the command line.

Usage:
  python manage.py recommend --lat 0.52 --lon 35.27 --ph 5.1 --n 148.5 --p 14.2 --k 312.5
  python manage.py recommend --continent Africa --country Nigeria --ph 6.2 --oc 0.6
  python manage.py recommend --state Karnataka --ph 6.8 --n 240

All soil params map to the same fields as the web form.
"""
from django.core.management.base import BaseCommand
from apps.recommendations.services import get_recommendations


class Command(BaseCommand):
    help = "Run a soil recommendation and print results"

    def add_arguments(self, parser):
        # Location
        parser.add_argument("--lat", type=float, help="Latitude")
        parser.add_argument("--lon", type=float, help="Longitude")
        parser.add_argument("--state", help="State name (India)")
        parser.add_argument("--continent", help="Continent name")
        parser.add_argument("--country", help="Country name")
        # Soil params
        parser.add_argument("--ph", type=float, required=True, help="Soil pH (required)")
        parser.add_argument("--oc", type=float)
        parser.add_argument("--ec", type=float)
        parser.add_argument("--n", type=float)
        parser.add_argument("--p", type=float)
        parser.add_argument("--k", type=float)
        parser.add_argument("--s", type=float)
        parser.add_argument("--fe", type=float)
        parser.add_argument("--mn", type=float)
        parser.add_argument("--cu", type=float)
        parser.add_argument("--zn", type=float)
        parser.add_argument("--b", type=float)
        parser.add_argument("--ca", type=float)
        parser.add_argument("--mg", type=float)

    def handle(self, *args, **options):
        data = {
            "lat": options["lat"],
            "lon": options["lon"],
            "state_name": options["state"],
            "continent_name": options["continent"],
            "country_name": options["country"],
            "ph": options["ph"],
            "oc": options.get("oc"),
            "ec": options.get("ec"),
            "n": options.get("n"),
            "p": options.get("p"),
            "k": options.get("k"),
            "s": options.get("s"),
            "fe": options.get("fe"),
            "mn": options.get("mn"),
            "cu": options.get("cu"),
            "zn": options.get("zn"),
            "b": options.get("b"),
            "ca": options.get("ca"),
            "mg": options.get("mg"),
        }

        try:
            result = get_recommendations(data)
        except (ValueError, LookupError) as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(f"\nLocation: {result['state'] or result['country']}"))
        self.stdout.write(f"Zone:     {result['zone']}")
        self.stdout.write(f"Continent: {result.get('continent', '')}")
        self.stdout.write(f"Country:   {result.get('country', '')}")
        self.stdout.write(f"Confidence: {result['confidence']} — {result['confidence_note']}")
        self.stdout.write(f"Crops evaluated: {result['crops_evaluated']}")
        self.stdout.write(f"Eliminated by pH: {result['crops_eliminated_by_ph']}")
        self.stdout.write("")

        for crop in result["top_crops"]:
            self.stdout.write(
                f"  #{crop['rank']} {crop['crop_name']:25s} "
                f"{crop['category']:15s} "
                f"{crop['total_score']:5.1f}/{crop['max_score']} "
                f"({crop['score_pct']:.0f}%)"
            )
            for d in crop["nutrient_deficiencies"]:
                self.stdout.write(f" [!] {d}")
            self.stdout.write("")
