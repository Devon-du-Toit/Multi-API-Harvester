import os
import requests
import json
from tqdm import tqdm
from ratelimit import limits, sleep_and_retry


# === Rate limit decorator ===
@sleep_and_retry
@limits(calls=60, period=60)
def call_api(url, params):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API request failed: {e}\nURL: {url}\nParams: {params}")
        raise


def search_results(supplied_api_url, species_name, max_results):
    url = supplied_api_url
    params = {
        "q": species_name,
        "per_page": 200,
        "order_by": "created_at",
        "photos": True,
        "quality_grade": "research",
        "page": 1,
    }

    results = []
    with tqdm(desc="Fetching observations") as pbar:
        while len(results) < max_results:
            try:
                data = call_api(url, params)["results"]
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                break

            if not data:
                break

            results.extend(data)
            params["page"] += 1
            pbar.update(len(data))

            if len(data) < params["per_page"]:
                break

    return results[:max_results]


def download_photos(observations, species_name, target_folder="downloads", max_photos_per_obs=5):
    safe_species = species_name.replace(" ", "_")
    for obs in tqdm(observations, desc="Downloading photos"):
        obs_id = obs["id"]
        photos = obs.get("photos", [])
        if not photos:
            continue

        folder = os.path.join(target_folder, safe_species, f"observation_{obs_id}")
        os.makedirs(folder, exist_ok=True)

        for idx, photo in enumerate(photos[:max_photos_per_obs], 1):
            url = photo.get("url").replace("square", "original")
            extension = url.split(".")[-1].split("?")[0]
            filename = f"photo_{idx}.{extension}"
            filepath = os.path.join(folder, filename)

            try:
                img_data = requests.get(url).content
                with open(filepath, "wb") as fp:
                    fp.write(img_data)
            except Exception as e:
                print(f"Failed to download {url}: {e}")


if __name__ == "__main__":
    # Load config
    with open("config.json", "r") as f:
        config = json.load(f)

    species = config.get("species_name", "").strip()
    max_obs = config.get("max_observations")
    max_photos = config.get("max_photos_per_observation")
    base_folder = config.get("base_folder", "downloads")
    api_url = config.get("api_url")

    if not species:
        raise ValueError("Species name must be provided in config.json")

    obs_list = search_results(api_url, species, max_results=max_obs)
    download_photos(obs_list, species, target_folder=base_folder, max_photos_per_obs=max_photos)



