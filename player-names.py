#!/usr/bin/env python3
import requests
import json
import re

def clean_player_name(name):
    """
    Scans the player name for any bracketed content.
    If the content is not one of the allowed tokens ("c", "wk", "rp", "ip")
    it prints that extra bracket text to the console.
    Then, it removes the allowed tokens (case-insensitive) and returns the cleaned name.
    """
    allowed = {"c", "wk", "rp", "ip"}
    bracket_contents = re.findall(r'\((.*?)\)', name)
    for content in bracket_contents:
        normalized = content.strip().lower()
        if normalized not in allowed:
            print(f"Extra bracket content encountered in player name '{name}': ({content})")
    cleaned = re.sub(r'\s*\((?:c|wk|rp|ip)\)', '', name, flags=re.IGNORECASE)
    return cleaned.strip()

def fetch_squad(match_number):
    """
    Fetches the squad data for a given match number.
    The URL follows the pattern:
      https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/{match_number}-squad.js?callback=onsquad
    The JSONP wrapper (onsquad(...);) is removed before returning the parsed JSON.
    """
    url = f"https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/{match_number}-squad.js?callback=onsquad"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching {url}: {response.status_code}")
    content = response.text
    json_text = re.sub(r"^onsquad\(", "", content)
    json_text = re.sub(r"\);\s*$", "", json_text)
    return json.loads(json_text)

def extract_players_from_squad(data):
    """
    Extracts players from the squad data.
    The JSON data contains two keys: 'squadA' and 'squadB'.
    For each player, it extracts the PlayerID, cleans the PlayerName,
    and also stores the TeamName.
    Returns a dictionary mapping PlayerID to a dictionary containing
    the cleaned player name and the team name.
    """
    players = {}
    for squad_key in ["squadA", "squadB"]:
        squad_list = data.get(squad_key, [])
        for player in squad_list:
            pid = player.get("PlayerID")
            raw_name = player.get("PlayerName", "").strip()
            cleaned_name = clean_player_name(raw_name)
            team = player.get("TeamName")
            if pid and cleaned_name:
                players[pid] = {"playerName": cleaned_name, "teamName": team}
    return players

def main():
    all_players = {}
    # Query squad data for matches 1799 to 1812 (inclusive)
    for match in range(1799, 1812):
        try:
            squad_data = fetch_squad(match)
            players = extract_players_from_squad(squad_data)
            # Combine the players; if a player appears in multiple matches, later entries will override earlier ones.
            for pid, info in players.items():
                all_players[pid] = info
        except Exception as e:
            print(f"Error processing match {match}: {e}")

    # Build a mapping from cleaned player names to a set of team names.
    name_to_teams = {}
    for info in all_players.values():
        name = info["playerName"]
        team = info["teamName"]
        if name:
            name_to_teams.setdefault(name, set()).add(team)

    # Print players that appear in multiple teams.
    for name, teams in name_to_teams.items():
        if len(teams) > 1:
            print(f"Player '{name}' appears in multiple teams: {', '.join(teams)}")

    # Calculate the number of unique teams.
    unique_teams = {info["teamName"] for info in all_players.values() if info["teamName"]}
    print(f"Number of unique teams extracted: {len(unique_teams)}")

    # Save the player data to a JSON file.
    with open("fpl-25/players.json", "w") as f:
        json.dump(all_players, f, indent=4)
    print(f"Extracted {len(all_players)} unique players from matches 1799 to 1812. Data stored in players.json.")

if __name__ == "__main__":
    main()
