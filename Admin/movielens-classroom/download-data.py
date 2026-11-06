"""Download the pinned MovieLens small dataset into ~/data/movielens-small."""
import argparse
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile

FILES = {
    "movies.csv": "5a5f32dd9bb3797b8e728a1b98958789d2b13f294a69fdfbc5727f8a9611aa07",
    "ratings.csv": "aa289ca83157595d0df6aea1be6a4ded676ddc4385472e8313a8ed9805352646",
    "tags.csv": "92a9f8bb7916dceef6151209845788c3643f794dfa79d1feaec7121b5960399d",
    "links.csv": "97ad18e4e56a09363c65676b6cb3482ce3e2cea2372a24620c1599c843325f31",
    "README.txt": "63d22ac138e80fae37021797ed8e1b9424b5239dc576a137422adf783ae3f404",
}
ARCHIVE_SHA256 = "696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436"
URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"


def checked(payloads):
    return all(hashlib.sha256(payloads[name]).hexdigest() == digest for name, digest in FILES.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Use the official HTTPS archive instead of a verified cached copy")
    args = parser.parse_args()
    target = Path.home() / "data" / "movielens-small"
    payloads = None
    if not args.download:
        for candidate in (target,):
            if all((candidate / name).is_file() for name in FILES):
                proposed = {name: (candidate / name).read_bytes() for name in FILES}
                if checked(proposed):
                    payloads = proposed
                    print("DATASET_CACHE_VERIFIED", candidate)
                    break
    if payloads is None:
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive = response.read(10 * 1024 * 1024 + 1)
        if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Official archive differs from the pinned classroom version; ask the instructor for the matching release")
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            payloads = {name: zipped.read("ml-latest-small/" + name) for name in FILES}
        if not checked(payloads):
            raise ValueError("Dataset file checksum failed")
        print("DATASET_DOWNLOAD_VERIFIED", URL)
    target.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        file = target / name
        if file.exists() and file.read_bytes() != payload:
            raise ValueError("Different classroom data already exists: " + str(file))
        file.write_bytes(payload)
    print("DATASET_READY", target)
    print("Expected: 9742 movies, 100836 ratings. Original README.txt retained.")


if __name__ == "__main__":
    main()
