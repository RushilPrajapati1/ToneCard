import argparse

from search import improved_search


def format_track(idx, track):
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    album = track.get("album", {}).get("name", "")
    url = track.get("external_urls", {}).get("spotify", "")
    return (
        f"{idx}. {track['name']} — {artists}\n"
        f"   album: {album} | popularity: {track.get('popularity', 0)}\n"
        f"   {url}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Spotify search improver — re-ranks results by vibe."
    )
    parser.add_argument("query", help='Search query, e.g. "rainy day jazz"')
    parser.add_argument(
        "--vibe",
        nargs="*",
        default=[],
        help="Vibe keywords used for re-ranking, e.g. --vibe chill lofi mellow",
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of results")
    parser.add_argument("--market", default="US", help="ISO market code")
    args = parser.parse_args()

    results = improved_search(
        args.query,
        vibe_keywords=args.vibe,
        limit=args.limit,
        market=args.market,
    )
    if not results:
        print("No results.")
        return

    for i, track in enumerate(results, 1):
        print(format_track(i, track))
        print()


if __name__ == "__main__":
    main()
