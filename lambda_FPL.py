import json
import requests
import gspread
import time
import re
# import timezone
import datetime
import dateutil
from dateutil import tz

# create map of all <players, score>

def lambda_handler(event, context):
    # TODO implement
    print("testing")
    handler()
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def handler():
    base_scorecard_url = "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/"
    match_num_offset = 1353

    gc = gspread.service_account(filename="./stellar-mariner-245520-3035a4005388.json")

    sh = gc.open_by_key("1Qex3w6Po8WF8jtznaNtkmzBPAB_vk_YJxkhJ0ivxqRE")

    gang = ["Farzi COE", "Farzi IT", "Sahoo", "Mittal", "Boss", "Sandy", "Kohli"]

    def calc_batting_score(batsman, batsmen):
        name = batsman["PlayerName"]
        name = name.strip()
        for ch in name:
            if ch == '(':
                name = name.split('(')[0]
                name = name.strip()
                break
        if batsmen.get(name) is None:
            return
        if batsman["PlayingOrder"] == "None" or batsman["PlayingOrder"] == None:
            return
        runs = batsman["Runs"]
        balls = batsman["Balls"]
        fours = batsman["Fours"]
        sixes = batsman["Sixes"]
        strike_rate = float(batsman["StrikeRate"])
        # calculate batting fantasy score
        score = runs + fours + 2*sixes
        if runs == 0:
            score -= 2
        elif runs >= 100:
            score += 16
        elif runs >= 50:
            score += 8
        elif runs >= 30:
            score += 4
        if balls >= 10:
            if strike_rate > 170:
                score += 6
            elif strike_rate > 150:
                score += 4
            elif strike_rate >= 130:
                score += 2
            elif strike_rate > 70:
                score += 0
            elif strike_rate >= 60:
                score += -2
            elif strike_rate >= 50:
                score += -4
            else: 
                score += -6
        batsmen[name] += score

    def calc_bowling_score(bowler, bowlers):
        name = bowler["PlayerName"]
        name = name.strip()
        for ch in name:
            if ch == '(':
                name = name.split('(')[0]
                name = name.strip()
                break
        if bowlers.get(name) is None:
            return
        overs = bowler["Overs"]
        maidens = bowler["Maidens"]
        wkts = bowler["Wickets"]
        economy = bowler["Economy"]

        score = 25*wkts + 12*maidens #+ 8*lbw_bowled[name]
        if wkts >= 5:
            score += 16
        elif wkts >= 4:
            score += 8
        elif wkts >= 3:
            score += 4
        
        if overs >= 2:
            if economy < 5:
                score += 6
            elif economy < 6:
                score += 4
            elif economy <= 7:
                score += 2
            elif economy < 10:
                score += 0
            elif economy <= 11:
                score += -2
            elif economy <= 12:
                score += -4
            else:
                score += -6
        bowlers[name] += score

    def calc_bowling_lbw_bold_score(batsman, bowlers):
        outDesc = batsman["OutDesc"]
        if outDesc == "not out":
            return
        if batsman["PlayingOrder"] == "None":
            return
        if outDesc.startswith("lbw") or outDesc.startswith("b "):
            bowler = batsman["BowlerName"]
            bowler = bowler.strip()
            if bowlers.get(bowler) is None:
                return
            bowlers[bowler] += 8

    def calc_sixes(batsman, six_hitters):
        name = batsman["PlayerName"]
        name = name.strip()
        for ch in name:
            if ch == '(':
                name = name.split('(')[0]
                name = name.strip()
                break
        if six_hitters.get(name) is None:
            return
        sixes = batsman["Sixes"]
        six_hitters[name] += sixes

    def calc_catches(batsman, catchers):
        name = ""
        if str(batsman["OutDesc"]).startswith("c & b"):
            name = str(batsman["OutDesc"]).split("c & b ")[1]
        elif str(batsman["OutDesc"]).startswith("c "):
            name = str(batsman["OutDesc"]).split("c ")[1].split(" b ")[0]
        if catchers.get(name) is None:
            return
        catchers[name] += 1

    def calc_wickets(bowler, wickets):
        name = bowler["PlayerName"]
        name = name.strip()
        for ch in name:
            if ch == '(':
                name = name.split('(')[0]
                name = name.strip()
                break
        if wickets.get(name) is None:
            return
        wkts = bowler["Wickets"]
        wickets[name] += wkts

    def calc_match_number():
        prev_match_number_range = sh.worksheet('Unsorted Scores').get('A7')
        in_progress_marker_range = sh.worksheet('Unsorted Scores').get('A100')
        in_progress_marker = in_progress_marker_range[0][0]
        prev_match_number = int(prev_match_number_range[0][0])
        if in_progress_marker == 'in_progress':
            # prev_match_number = int(prev_match_number)
            match_summary_url = base_scorecard_url + str(match_num_offset + prev_match_number) + '-matchsummary.js'
            try:
                # Fetch the JavaScript file
                response = requests.get(match_summary_url)
                response.raise_for_status()  # Raise an exception for HTTP errors

                # Extract the parameter passed to onScoring()
                match = re.search(r'onScoringMatchsummary\((.*?)\);', response.text, re.DOTALL)
                if match:
                    json_string = match.group(1).strip()
                    if "Won By" in json_string:
                        sh.worksheet("Unsorted Scores").update('A100', 'finished')
                    return prev_match_number
                else:
                    print("No match found for onScoringMatchsummary() function call.")
            except requests.RequestException as e:
                print("Error fetching file:", e)
                return 0
        else:
            match_summary_url = base_scorecard_url + str(match_num_offset + prev_match_number + 1) + '-matchsummary.js'
            try:
                # Fetch the JavaScript file
                response = requests.get(match_summary_url)
                response.raise_for_status()  # Raise an exception for HTTP errors

                # Extract the parameter passed to onScoring()
                match = re.search(r'onScoringMatchsummary\((.*?)\);', response.text, re.DOTALL)
                if match:
                    json_string = match.group(1).strip()
                    if "Won By" in json_string:
                        sh.worksheet("Unsorted Scores").update('A7', prev_match_number + 1)
                    else:
                        sh.worksheet("Unsorted Scores").update('A7', prev_match_number + 1)
                        sh.worksheet("Unsorted Scores").update('A100', 'in_progress')
                    return prev_match_number + 1
                else:
                    print("No match found for onScoringMatchsummary() function call.")
            except requests.RequestException as e:
                print("Error fetching file:", e)
                return 0
        return 0
         
    match_num = calc_match_number()
    if match_num == 0:
        return
    
    for match_number in range(match_num, match_num + 1):
        base_url = base_scorecard_url + str(match_num_offset + match_number)
        innings = ["Innings1", "Innings2"]

        battingCard = []
        bowlingCard = []
        for inning in innings:
            url = base_url + "-" + inning + ".js"
            try:
                # Fetch the JavaScript file
                response = requests.get(url)
                response.raise_for_status()  # Raise an exception for HTTP errors

                # Extract the parameter passed to onScoring()
                match = re.search(r'onScoring\((.*?)\);', response.text, re.DOTALL)
                if match:
                    json_string = match.group(1).strip()
                    json_data = json.loads(json_string)
                    battingCard.append(json_data[inning]["BattingCard"])
                    bowlingCard.append(json_data[inning]["BowlingCard"])
                    # print(json_data)
                else:
                    print("No match found for onScoring() function call.")
            except requests.RequestException as e:
                print("Error fetching file:", e)
 
        if len(battingCard) == 0:
            return
        for gang_member in gang:
            batsmen = {}
            bowlers = {}
            six_hitters = {}
            catchers = {}
            wickets = {}
            scores_for_match = [[]]
            print("\n##" + gang_member + "##")
            players = sh.worksheet(gang_member).get('B2:AY2')
            for i in range(5):
                player = players[0][i]
                player = player.split('+')[0].strip()
                batsmen[player] = 0

            for i in range(5):
                player = players[0][6+i]
                player = player.split('+')[0].strip()
                bowlers[player] = 0

            for i in range(12):
                player = players[0][12+i]
                six_hitters[player] = 0

            for i in range(12):
                player = players[0][25+i]
                catchers[player] = 0
            
            for i in range(12):
                player = players[0][38+i]
                wickets[player] = 0

            for inning in range(0, len(battingCard), 1):
                for batsman in battingCard[inning]:
                    calc_batting_score(batsman, batsmen)
                    calc_bowling_lbw_bold_score(batsman, bowlers)

                for bowler in bowlingCard[inning]:
                    calc_bowling_score(bowler, bowlers)
                
                for player in battingCard[inning]:
                    calc_sixes(player, six_hitters)
                
                for player in battingCard[inning]:
                    calc_catches(player, catchers)

                for player in bowlingCard[inning]:
                    calc_wickets(player, wickets)

            for player in catchers:
                batScore = 0
                bowlScore = 0
                if player in batsmen:
                    batScore = batsmen[player]
                if player in bowlers:
                    bowlScore = bowlers[player]
                if batScore == 0 and bowlScore == 0 and catchers[player] == 0:
                    continue
                print(player)
                print("     Batting " + str(batScore))
                print("     Bowling " + str(bowlScore))
                print("     Sixes " + str(six_hitters[player]))
                print("     Catches " + str(catchers[player]))
                print("     Wickets " + str(wickets[player]))

            for i in range(5):
                scores_for_match[0].append(batsmen[players[0][i].split('+')[0].strip()])
            scores_for_match[0].append("")

            # Multiply bowling points by 1.25 before appending
            for i in range(5):
                scores_for_match[0].append(bowlers[players[0][6+i].split('+')[0].strip()] * 1.25)
            scores_for_match[0].append('=SUM(B' + str(match_number + 2) + ':L' + str(match_number + 2) + ')')
            
            for i in range(12):
                scores_for_match[0].append(six_hitters[players[0][12+i]])
            scores_for_match[0].append("")

            for i in range(12):
                scores_for_match[0].append(catchers[players[0][25+i]])
            scores_for_match[0].append("")

            for i in range(12):
                scores_for_match[0].append(wickets[players[0][38+i]])
            
            sh.worksheet(gang_member).update('B' + str(match_number + 2) + ":AY" + str(match_number + 2), scores_for_match, value_input_option='USER_ENTERED')
        
        sh.worksheet("Unsorted Scores").update('A7', match_number)
        # time.sleep(20)

    final_points = sh.worksheet("Leaderboard").get('B24:O30')
    total_winnings = [25000, 25000, 12500, 6250, 6250, 6250, 6250]
    overall_winnings = {}

    actual_winnings = [row[:] for row in final_points]

    for player in range(7):
        overall_winnings[final_points[player][0]] = -12500
        for category in range(7):
            actual_winnings[player][category*2 + 1] = 0

    for category in range(7):
        top_score = final_points[0][category*2 + 1]
        player = 0
        while(final_points[player][category*2 + 1] == top_score):
            player += 1
        # if top spot shared by more than 1
        if player > 1:
            amt = total_winnings[category] / player
            for i in range(player):
                actual_winnings[i][category*2 + 1] = amt
                overall_winnings[actual_winnings[i][category*2]] += amt
        else:
            actual_winnings[0][category*2 + 1] = 0.7 * total_winnings[category]
            overall_winnings[actual_winnings[0][category*2]] += 0.7 * total_winnings[category]
            second_top_score = final_points[1][category*2 + 1]
            while(final_points[player][category*2 + 1] == second_top_score):
                player += 1
            count_of_players = player - 1
            if count_of_players == 0:
                print(category)
                print(player)
            amt = float((0.3 * total_winnings[category])) / count_of_players
            for i in range(count_of_players):
                actual_winnings[i+1][category*2 + 1] = amt
                overall_winnings[actual_winnings[i+1][category*2]] += amt

    for key, val in overall_winnings.items():
        print(key + " " + str(val))

    final_winnings = []
    for player in range(7):
        final_winnings.append([final_points[player][0], overall_winnings[final_points[player][0]]])

    # print(final_winnings)
    sorted_final_winnings = sorted(final_winnings, key=lambda x: x[1], reverse=True)

    sh.worksheet("Leaderboard").update('B34:040', actual_winnings)
    sh.worksheet("Leaderboard").update('H43:I49', sorted_final_winnings)
    # ind_time = datetime.now(timezone("Asia/Kolkata")).strftime("%d/%m/%Y %H:%M:%S")
    IST = dateutil.tz.gettz('Asia/Kolkata')
    ind_time = datetime.datetime.now(tz=IST).strftime("%d/%m/%Y %H:%M:%S")
    # sh.worksheet("Leaderboard").update('B5', [[str(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))]])
    sh.worksheet("Leaderboard").update('B5', [[str(ind_time)]])