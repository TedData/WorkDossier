from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


app = Flask(__name__)


STOPS = {

    '600251': 'https://jp.translink.com.au/plan-your-journey/stops/600251',

    "010228": "https://jp.translink.com.au/plan-your-journey/stops/010228",

    '004970': 'https://jp.translink.com.au/plan-your-journey/stops/004970'

}


TARGET_ROUTES = {

    "010228": [
        "210",
        "212",
        "214",
        "215",
        "220"
    ],

    "004970": [
        "185"
    ],

    "600251": [
        "clsh",
        "clbr",
        "shorncliffe",
        "brisbanecity",
        "brisbane"
    ]

}


HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )

}



def adjust_depart(depart, route):

    if str(route).lower() != "210":

        return depart


    now = datetime.now()

    depart_lower = depart.lower().strip()


    if depart_lower == "now":

        return "Now"



    if "min" in depart_lower:

        minutes = int(
            depart_lower
            .replace("min", "")
            .strip()
        )


        minutes = max(minutes - 1, 0)


        if minutes == 0:

            return "Now"


        return f"{minutes} min"



    if "scheduled" in depart_lower:


        time_str = (
            depart_lower
            .replace("(scheduled)", "")
            .strip()
        )


        scheduled_time = datetime.strptime(
            time_str,
            "%I:%M %p"
        )


        scheduled_time = scheduled_time.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )


        scheduled_time -= timedelta(minutes=1)


        return (
            scheduled_time.strftime("%I:%M %p")
            + " (scheduled)"
        )


    return depart





def get_departures(url):


    r = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )


    r.raise_for_status()



    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )



    tables = soup.find_all("table")



    buses = []



    for table in tables:


        rows = table.find_all("tr")



        for row in rows:


            cols = row.find_all("td")


            if len(cols) < 2:

                continue



            depart = cols[0].get_text(
                " ",
                strip=True
            )



            service = cols[1].get_text(
                " ",
                strip=True
            )



            route = (
                service
                .split()[0]
                .replace(" ", "")
                .lower()
            )



            if route in TARGET_ROUTES["600251"]:


                route = "CLSH"

                service = "To South Bank"



            elif route in TARGET_ROUTES["004970"]:


                service = "To Woolloongabba"



            elif route in TARGET_ROUTES["010228"]:


                service = "To Queen St"



            else:

                continue




            buses.append({

                "route": route,

                "depart": adjust_depart(
                    depart,
                    route
                ),

                "service": service

            })



    return buses







def convert_depart(depart):


    now = datetime.now()


    depart = depart.lower().strip()



    if depart == "now":

        return now



    if "min" in depart:


        minutes = int(
            depart
            .replace("min", "")
            .strip()
        )


        return now + timedelta(
            minutes=minutes
        )



    if "scheduled" in depart:


        time_str = (
            depart
            .replace("(scheduled)", "")
            .strip()
        )


        scheduled_time = datetime.strptime(
            time_str,
            "%I:%M %p"
        )


        scheduled_time = scheduled_time.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )



        if scheduled_time < now:

            scheduled_time += timedelta(
                days=1
            )


        return scheduled_time



    return datetime.max







def get_bus_result():


    buses = []



    for stop_id, url in STOPS.items():


        try:


            result = get_departures(url)



            if result:

                buses.append(result)



        except Exception as e:


            print(
                "Error:",
                e
            )




    if not buses:

        return []




    all_buses = [

        item

        for group in buses

        for item in group

    ]





    sorted_buses = sorted(

        all_buses,

        key=lambda x:
            convert_depart(
                x["depart"]
            )

    )




    result = []



    route_count = {}




    for bus in sorted_buses:



        route = bus["route"]



        if route_count.get(route, 0) >= 300:

            continue




        route_count[route] = (
            route_count.get(route, 0)
            + 1
        )




        result.append({

            "route": route,

            "time": bus["depart"],

            "direction": bus["service"]

        })



    return result







@app.route("/bus", methods=["GET"])
def bus():


    data = get_bus_result()


    return jsonify(data)







@app.route("/", methods=["GET"])
def home():

    return "Bus API is running"







if __name__ == "__main__":


    app.run(
        host="0.0.0.0",
        port=5000
    )