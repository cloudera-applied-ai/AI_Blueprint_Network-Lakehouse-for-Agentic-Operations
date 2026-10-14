"""Constants for Cable Network ISP Data Lakehouse"""

# ============================================
# Service Areas (US Metro Markets)
# ============================================

SERVICE_AREAS = [
    "Charlotte", "Dallas-Fort Worth", "Los Angeles", "Tampa Bay",
    "Columbus", "New York City", "Chicago", "Denver", "Atlanta", "Seattle",
    "Phoenix", "Minneapolis", "Miami", "Boston", "Portland",
    "Kansas City", "Nashville", "San Antonio", "Detroit", "Salt Lake City",
    "Toronto", "Vancouver", "Mexico City", "Sao Paulo", "Buenos Aires",
    "London", "Frankfurt", "Paris",
    "Dubai", "Cairo",
    "Mumbai", "Tokyo", "Seoul", "Singapore", "Jakarta",
    "Sydney", "Melbourne",
    "Lagos", "Johannesburg", "Nairobi",
]

SERVICE_AREA_CONFIG = {
    "Charlotte": {
        "state": "NC",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [34.0, 36.2],
        "lng_bounds": [-82.0, -79.5],
        "cities": [
            "Charlotte", "Concord", "Gastonia", "Huntersville", "Mooresville",
            "Rock Hill", "Matthews", "Mint Hill", "Statesville", "Salisbury",
            "Monroe", "Indian Trail", "Waxhaw", "Kannapolis",
        ],
    },
    "Dallas-Fort Worth": {
        "state": "TX",
        "headend_count": 1,
        "hub_count": 6,
        "nodes_per_hub": 40,
        "lat_bounds": [31.5, 34.0],
        "lng_bounds": [-98.5, -95.5],
        "cities": [
            "Dallas", "Fort Worth", "Arlington", "Plano", "Irving", "Garland",
            "Frisco", "McKinney", "Denton", "Richardson", "Waxahachie",
            "Weatherford", "Rockwall", "Mansfield", "Lewisville", "Corsicana",
        ],
    },
    "Los Angeles": {
        "state": "CA",
        "headend_count": 2,
        "hub_count": 8,
        "nodes_per_hub": 40,
        "lat_bounds": [33.0, 35.2],
        "lng_bounds": [-119.8, -116.5],
        "cities": [
            "Los Angeles", "Long Beach", "Anaheim", "Santa Ana", "Glendale",
            "Pasadena", "Torrance", "Burbank", "Inglewood", "Downey",
            "Riverside", "Ontario", "Palmdale", "Santa Clarita", "Pomona", "Ventura",
        ],
    },
    "Tampa Bay": {
        "state": "FL",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [26.8, 29.2],
        "lng_bounds": [-83.4, -81.3],
        "cities": [
            "Tampa", "St. Petersburg", "Clearwater", "Brandon", "Largo",
            "Palm Harbor", "Wesley Chapel", "Riverview", "Lakeland",
            "Bradenton", "Spring Hill", "New Port Richey", "Plant City", "Zephyrhills",
        ],
    },
    "Columbus": {
        "state": "OH",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [38.9, 41.0],
        "lng_bounds": [-84.2, -81.8],
        "cities": [
            "Columbus", "Dublin", "Westerville", "Reynoldsburg", "Grove City",
            "Hilliard", "Gahanna", "Upper Arlington", "Zanesville", "Lancaster",
            "Delaware", "Marion", "Circleville", "Chillicothe",
        ],
    },
    "New York City": {
        "state": "NY",
        "headend_count": 2,
        "hub_count": 7,
        "nodes_per_hub": 40,
        "lat_bounds": [39.8, 41.8],
        "lng_bounds": [-75.2, -72.5],
        "cities": [
            "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island",
            "Yonkers", "New Rochelle", "White Plains", "Newark", "Jersey City",
            "Stamford", "Paterson", "Morristown", "Hempstead", "Huntington", "Middletown",
        ],
    },
    "Chicago": {
        "state": "IL",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [40.7, 43.0],
        "lng_bounds": [-89.5, -86.5],
        "cities": [
            "Chicago", "Bolingbrook", "Naperville", "Joliet", "Elgin", "Schaumburg",
            "Evanston", "Oak Park", "Cicero", "Berwyn", "Waukegan",
            "DeKalb", "Kankakee", "Crystal Lake", "Plainfield", "Woodstock",
        ],
    },
    "Denver": {
        "state": "CO",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [38.8, 40.8],
        "lng_bounds": [-106.2, -103.8],
        "cities": [
            "Denver", "Aurora", "Lakewood", "Thornton", "Arvada", "Westminster",
            "Centennial", "Boulder", "Littleton", "Broomfield", "Castle Rock",
            "Longmont", "Golden", "Parker", "Brighton", "Erie",
        ],
    },
    "Atlanta": {
        "state": "GA",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [32.7, 35.0],
        "lng_bounds": [-85.5, -83.0],
        "cities": [
            "Atlanta", "Sandy Springs", "Roswell", "Johns Creek", "Alpharetta",
            "Marietta", "Smyrna", "Brookhaven", "Dunwoody", "Kennesaw",
            "Cartersville", "Newnan", "Covington", "McDonough", "Peachtree City", "Canton",
        ],
    },
    "Seattle": {
        "state": "WA",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [46.5, 48.6],
        "lng_bounds": [-123.3, -121.0],
        "cities": [
            "Seattle", "Bellevue", "Tacoma", "Kent", "Renton", "Federal Way",
            "Kirkland", "Redmond", "Bothell", "Lynnwood", "Everett",
            "Olympia", "Puyallup", "Bremerton", "Snohomish", "Auburn",
        ],
    },
    "Phoenix": {
        "state": "AZ",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [32.2, 34.4],
        "lng_bounds": [-113.2, -110.8],
        "cities": [
            "Phoenix", "Mesa", "Chandler", "Scottsdale", "Gilbert", "Tempe",
            "Avondale", "Peoria", "Surprise", "Buckeye", "Apache Junction",
            "Casa Grande", "Maricopa", "Fountain Hills",
        ],
    },
    "Minneapolis": {
        "state": "MN",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [44.0, 46.0],
        "lng_bounds": [-94.5, -92.0],
        "cities": [
            "Minneapolis", "St. Paul", "Bloomington", "Plymouth", "Brooklyn Park",
            "Maple Grove", "Eagan", "Eden Prairie", "Stillwater", "Woodbury",
            "Lakeville", "Shakopee", "Burnsville", "Chaska",
        ],
    },
    "Miami": {
        "state": "FL",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [24.8, 27.4],
        "lng_bounds": [-81.2, -79.5],
        "cities": [
            "Miami", "Fort Lauderdale", "Hollywood", "Hialeah", "Coral Springs",
            "Pembroke Pines", "Miramar", "Davie", "Boca Raton", "Homestead",
            "Delray Beach", "Jupiter", "Deerfield Beach", "Cutler Bay",
        ],
    },
    "Boston": {
        "state": "MA",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [41.4, 43.2],
        "lng_bounds": [-72.2, -70.0],
        "cities": [
            "Boston", "Cambridge", "Quincy", "Newton", "Somerville", "Brookline",
            "Waltham", "Medford", "Lowell", "Brockton", "Gloucester",
            "Framingham", "Peabody", "Woburn",
        ],
    },
    "Portland": {
        "state": "OR",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [44.3, 46.3],
        "lng_bounds": [-123.6, -121.5],
        "cities": [
            "Portland", "Beaverton", "Hillsboro", "Gresham", "Lake Oswego",
            "Tigard", "Tualatin", "Oregon City", "McMinnville", "Wilsonville",
            "Canby", "Newberg", "Woodburn", "Milwaukie",
        ],
    },
    "Kansas City": {
        "state": "MO",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [38.1, 40.0],
        "lng_bounds": [-95.8, -93.5],
        "cities": [
            "Kansas City", "Overland Park", "Olathe", "Independence",
            "Lee's Summit", "Shawnee", "Blue Springs", "Lenexa",
            "Liberty", "Lawrence", "Leavenworth", "Belton", "Bonner Springs", "Grain Valley",
        ],
    },
    "Nashville": {
        "state": "TN",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [35.0, 37.0],
        "lng_bounds": [-88.0, -85.5],
        "cities": [
            "Nashville", "Murfreesboro", "Franklin", "Hendersonville", "Gallatin",
            "Mount Juliet", "Lebanon", "Brentwood", "Clarksville", "Dickson",
            "Columbia", "Springfield", "Shelbyville", "Nolensville",
        ],
    },
    "San Antonio": {
        "state": "TX",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [28.4, 30.5],
        "lng_bounds": [-99.8, -97.0],
        "cities": [
            "San Antonio", "New Braunfels", "San Marcos", "Schertz", "Cibolo",
            "Converse", "Universal City", "Live Oak", "Seguin", "Boerne",
            "Floresville", "Castroville", "Pleasanton", "Hondo",
        ],
    },
    "Detroit": {
        "state": "MI",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [41.4, 43.3],
        "lng_bounds": [-84.5, -82.0],
        "cities": [
            "Detroit", "Warren", "Sterling Heights", "Dearborn", "Livonia",
            "Troy", "Southfield", "Royal Oak", "Ann Arbor", "Pontiac",
            "Novi", "Westland", "Ypsilanti", "Howell",
        ],
    },
    "Salt Lake City": {
        "state": "UT",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [39.5, 42.0],
        "lng_bounds": [-113.0, -110.5],
        "cities": [
            "Salt Lake City", "West Valley City", "Provo", "Sandy", "Orem",
            "Ogden", "West Jordan", "Layton", "Park City", "Tooele",
            "American Fork", "Lehi", "Bountiful", "Draper",
        ],
    },
    # ============================================
    # International Markets
    # ============================================
    "Toronto": {
        "state": "ON",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [42.8, 45.0],
        "lng_bounds": [-80.5, -78.0],
        "cities": [
            "Toronto", "Mississauga", "Brampton", "Markham", "Vaughan",
            "Richmond Hill", "Oakville", "Burlington", "Pickering",
            "Ajax", "Whitby", "Oshawa", "Milton", "Georgetown",
        ],
    },
    "Mexico City": {
        "state": "CDMX",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [18.5, 20.5],
        "lng_bounds": [-100.0, -98.0],
        "cities": [
            "Mexico City", "Ecatepec", "Naucalpan", "Tlalnepantla",
            "Coacalco", "Tultitlan", "Atizapan", "Cuautitlan",
            "Texcoco", "Chalco", "Ixtapaluca", "Huixquilucan",
        ],
    },
    "Sao Paulo": {
        "state": "SP",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [-24.5, -22.5],
        "lng_bounds": [-48.0, -45.5],
        "cities": [
            "Sao Paulo", "Guarulhos", "Campinas", "Santo Andre",
            "Osasco", "Sorocaba", "Barueri", "Diadema",
            "Jundiai", "Mogi das Cruzes", "Carapicuiba", "Suzano",
        ],
    },
    "London": {
        "state": "ENG",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [50.8, 52.2],
        "lng_bounds": [-1.0, 0.8],
        "cities": [
            "London", "Reading", "Croydon", "Watford", "Slough",
            "Guildford", "Dartford", "Bromley", "Enfield",
            "Harrow", "Romford", "Kingston", "Epsom", "Luton",
        ],
    },
    "Frankfurt": {
        "state": "HE",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [49.5, 50.9],
        "lng_bounds": [7.8, 9.5],
        "cities": [
            "Frankfurt", "Wiesbaden", "Darmstadt", "Offenbach",
            "Mainz", "Hanau", "Bad Homburg", "Friedberg",
            "Ruesselsheim", "Oberursel", "Giessen", "Marburg",
        ],
    },
    "Dubai": {
        "state": "DXB",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [23.5, 25.8],
        "lng_bounds": [53.5, 56.5],
        "cities": [
            "Dubai", "Abu Dhabi", "Sharjah", "Ajman",
            "Al Ain", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain",
            "Khor Fakkan", "Dibba Al Fujairah", "Kalba", "Madinat Zayed",
        ],
    },
    "Mumbai": {
        "state": "MH",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [18.4, 20.0],
        "lng_bounds": [72.3, 73.8],
        "cities": [
            "Mumbai", "Thane", "Navi Mumbai", "Kalyan",
            "Vasai", "Panvel", "Bhiwandi", "Mira Bhayandar",
            "Ulhasnagar", "Ambernath", "Badlapur", "Alibaug",
        ],
    },
    "Tokyo": {
        "state": "TK",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [35.0, 36.2],
        "lng_bounds": [138.8, 140.4],
        "cities": [
            "Tokyo", "Yokohama", "Kawasaki", "Saitama",
            "Chiba", "Sagamihara", "Hachioji", "Machida",
            "Fuchu", "Tachikawa", "Musashino", "Mitaka",
        ],
    },
    "Singapore": {
        "state": "SG",
        "headend_count": 1,
        "hub_count": 3,
        "nodes_per_hub": 40,
        "lat_bounds": [1.2, 1.5],
        "lng_bounds": [103.6, 104.0],
        "cities": [
            "Singapore", "Jurong East", "Tampines", "Woodlands",
            "Ang Mo Kio", "Bedok", "Clementi", "Bukit Batok",
            "Sengkang", "Punggol", "Yishun", "Hougang",
        ],
    },
    "Sydney": {
        "state": "NSW",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [-34.5, -33.0],
        "lng_bounds": [150.0, 151.8],
        "cities": [
            "Sydney", "Parramatta", "Penrith", "Liverpool",
            "Campbelltown", "Blacktown", "Hornsby", "Manly",
            "Bankstown", "Sutherland", "Ryde", "Chatswood",
        ],
    },
    # ============================================
    # Additional International Markets
    # ============================================
    "Vancouver": {
        "state": "BC",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [48.8, 49.8],
        "lng_bounds": [-124.0, -122.5],
        "cities": [
            "Vancouver", "Surrey", "Burnaby", "Richmond",
            "Coquitlam", "Delta", "Langley", "Abbotsford",
            "North Vancouver", "New Westminster", "Chilliwack", "Squamish",
        ],
    },
    "Buenos Aires": {
        "state": "BA",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [-35.0, -34.2],
        "lng_bounds": [-59.0, -58.0],
        "cities": [
            "Buenos Aires", "La Plata", "Quilmes", "Lomas de Zamora",
            "Lanus", "Avellaneda", "San Isidro", "Tigre",
            "Pilar", "Moreno", "Merlo", "San Martin",
        ],
    },
    "Paris": {
        "state": "IDF",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [48.5, 49.2],
        "lng_bounds": [1.8, 3.0],
        "cities": [
            "Paris", "Versailles", "Boulogne-Billancourt", "Saint-Denis",
            "Montreuil", "Nanterre", "Creteil", "Argenteuil",
            "Meaux", "Evry", "Pontoise", "Melun",
        ],
    },
    "Seoul": {
        "state": "SEL",
        "headend_count": 1,
        "hub_count": 5,
        "nodes_per_hub": 40,
        "lat_bounds": [37.2, 37.8],
        "lng_bounds": [126.6, 127.5],
        "cities": [
            "Seoul", "Incheon", "Suwon", "Seongnam",
            "Goyang", "Yongin", "Bucheon", "Ansan",
            "Anyang", "Uijeongbu", "Gwangmyeong", "Siheung",
        ],
    },
    "Jakarta": {
        "state": "JKT",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [-6.6, -6.0],
        "lng_bounds": [106.4, 107.2],
        "cities": [
            "Jakarta", "Bogor", "Depok", "Tangerang",
            "Bekasi", "South Tangerang", "Cikarang", "Cibinong",
            "Serpong", "Karawang", "Cilegon", "Serang",
        ],
    },
    "Melbourne": {
        "state": "VIC",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [-38.2, -37.4],
        "lng_bounds": [144.4, 145.6],
        "cities": [
            "Melbourne", "Geelong", "Ballarat", "Dandenong",
            "Frankston", "Werribee", "Sunbury", "Melton",
            "Cranbourne", "Pakenham", "Berwick", "Mornington",
        ],
    },
    "Cairo": {
        "state": "CAI",
        "headend_count": 1,
        "hub_count": 3,
        "nodes_per_hub": 40,
        "lat_bounds": [29.8, 30.5],
        "lng_bounds": [31.0, 31.8],
        "cities": [
            "Cairo", "Giza", "Helwan", "Nasr City",
            "Maadi", "Heliopolis", "October City", "Shubra",
            "Obour", "New Cairo", "Badr", "Shorouk",
        ],
    },
    "Lagos": {
        "state": "LG",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [6.3, 6.8],
        "lng_bounds": [3.0, 3.7],
        "cities": [
            "Lagos Island", "Ikeja", "Lekki", "Victoria Island",
            "Surulere", "Mushin", "Ikorodu", "Badagry",
            "Epe", "Ajah", "Agege", "Oshodi",
        ],
    },
    "Johannesburg": {
        "state": "GP",
        "headend_count": 1,
        "hub_count": 4,
        "nodes_per_hub": 40,
        "lat_bounds": [-26.6, -25.8],
        "lng_bounds": [27.5, 28.6],
        "cities": [
            "Johannesburg", "Pretoria", "Sandton", "Soweto",
            "Centurion", "Midrand", "Randburg", "Roodepoort",
            "Germiston", "Benoni", "Boksburg", "Kempton Park",
        ],
    },
    "Nairobi": {
        "state": "NBO",
        "headend_count": 1,
        "hub_count": 3,
        "nodes_per_hub": 40,
        "lat_bounds": [-1.6, -1.0],
        "lng_bounds": [36.5, 37.2],
        "cities": [
            "Nairobi CBD", "Thika", "Kiambu", "Machakos",
            "Ruiru", "Juja", "Kitengela", "Athi River",
            "Limuru", "Ngong", "Karuri", "Kikuyu",
        ],
    },
}

# ============================================
# Equipment Manufacturers
# ============================================

MANUFACTURERS = ["Cisco", "CommScope/ARRIS", "Harmonic", "Technetix", "ATX Networks", "Teleste"]

NODE_MANUFACTURERS = {
    "Cisco": ["GS7000", "GS7000 Hub Node", "GS7000 Segmentable Node"],
    "CommScope/ARRIS": ["NC4000", "NC4000e", "NC2000H"],
    "Harmonic": ["CableOS Node", "CableOS Virtual Node"],
    "Technetix": ["DBx Digital Node", "DBx Compact"],
    "ATX Networks": ["GigaXtend HDe", "GigaXtend HDE Pro"],
}

CMTS_MANUFACTURERS = {
    "Cisco": ["cBR-8", "cBR-8 CIN"],
    "Casa": ["C100G", "C40G"],
    "Harmonic": ["CableOS Platform", "CableOS Cloud"],
}

MODEM_MANUFACTURERS = {
    "ARRIS": ["SB8200", "S33", "TG4482A", "SB6190"],
    "Motorola": ["MB8611", "MB8600", "MG8725"],
    "Hitron": ["CODA56", "CODA5610", "CODA4582"],
    "Netgear": ["CM2000", "CM1200", "CM1000"],
}

AMPLIFIER_MANUFACTURERS = {
    "CommScope/ARRIS": ["MB7600", "1GHz Line Extender", "1.2GHz Trunk Amp", "Bridger Amp"],
    "Technetix": ["UBB1200", "UBA1200", "DBx Amp"],
    "ATX Networks": ["MaxNet 1.2G", "GigaXtend LE", "XS Series"],
    "Teleste": ["AC8000", "AC3000", "AC3200 LE"],
}

HVAC_MANUFACTURERS = ["Vertiv", "Schneider Electric", "Emerson", "Delta", "Juniper Networks"]

# ============================================
# DOCSIS Configuration
# ============================================

DOCSIS_VERSIONS = ["3.0", "3.1", "4.0"]

DOCSIS_VERSION_DISTRIBUTION = {
    "3.0": 0.20,
    "3.1": 0.50,
    "4.0": 0.30,
}

NODE_TYPES = ["N+0", "N+1", "N+2", "N+3"]

NODE_TYPE_DISTRIBUTION = {
    "N+0": 0.15,
    "N+1": 0.25,
    "N+2": 0.35,
    "N+3": 0.25,
}

NODE_TYPE_CONFIG = {
    "N+0": {"amplifier_cascade": 0, "homes_passed_range": (100, 250), "desc": "Fiber deep, no amplifiers"},
    "N+1": {"amplifier_cascade": 1, "homes_passed_range": (150, 350), "desc": "One amplifier in cascade"},
    "N+2": {"amplifier_cascade": 2, "homes_passed_range": (200, 400), "desc": "Two amplifiers in cascade"},
    "N+3": {"amplifier_cascade": 3, "homes_passed_range": (250, 500), "desc": "Three amplifiers in cascade"},
}

FREQUENCY_PLANS = {
    "upstream": {"min_mhz": 5, "max_mhz": 42, "label": "Upstream (5-42 MHz)"},
    "downstream": {"min_mhz": 54, "max_mhz": 1002, "label": "Downstream (54-1002 MHz)"},
    "ofdm": {"min_mhz": 1002, "max_mhz": 1218, "label": "OFDM (1002-1218 MHz)"},
}

DOCSIS_CHANNEL_CONFIGS = {
    "3.0": {"ds_channels": (16, 24), "us_channels": (4, 4), "ofdm_channels": (0, 0), "ofdma_channels": (0, 0)},
    "3.1": {"ds_channels": (24, 32), "us_channels": (4, 8), "ofdm_channels": (1, 2), "ofdma_channels": (1, 2)},
    "4.0": {"ds_channels": (32, 32), "us_channels": (8, 8), "ofdm_channels": (2, 2), "ofdma_channels": (2, 2)},
}

# ============================================
# Service Plans
# ============================================

SERVICE_PLANS = {
    "Internet 200": {"download_mbps": 200, "upload_mbps": 10, "monthly_rate": 49.99},
    "Internet 400": {"download_mbps": 400, "upload_mbps": 20, "monthly_rate": 69.99},
    "Internet 1000": {"download_mbps": 1000, "upload_mbps": 35, "monthly_rate": 89.99},
    "Gig+": {"download_mbps": 1200, "upload_mbps": 50, "monthly_rate": 109.99},
}

SERVICE_PLAN_DISTRIBUTION = {
    "Internet 200": 0.30,
    "Internet 400": 0.35,
    "Internet 1000": 0.25,
    "Gig+": 0.10,
}

# ============================================
# Alert Types (Cable Network)
# ============================================

ALERT_TYPES = [
    "NODE_OUTAGE",
    "CMTS_CARD_FAILURE",
    "HIGH_NOISE_INGRESS",
    "POWER_SUPPLY_FAILURE",
    "AMPLIFIER_FAILURE",
    "UPSTREAM_CONGESTION",
    "DOWNSTREAM_CONGESTION",
    "PLANT_DAMAGE",
    "CPE_MASS_OFFLINE",
    "SIGNAL_DEGRADATION",
    "TEMPERATURE_ALARM",
    "CAPACITY_THRESHOLD",
    "FIRMWARE_ISSUE",
    "RANGING_FAILURE",
    "MAINTENANCE_OVERRUN",
    "GATING_FAILURE",
]

ALERT_SEVERITIES = ["CRITICAL", "WARNING", "INFO"]

ALERT_DESCRIPTIONS = {
    "NODE_OUTAGE": ("Fiber Node Outage", "Complete loss of service at fiber node"),
    "CMTS_CARD_FAILURE": ("CMTS Card Failure", "CMTS line card failure detected"),
    "HIGH_NOISE_INGRESS": ("High Noise Ingress", "Upstream noise floor elevated above threshold"),
    "POWER_SUPPLY_FAILURE": ("Power Supply Failure", "Node power supply has failed or degraded"),
    "AMPLIFIER_FAILURE": ("Amplifier Failure", "RF amplifier failure in cascade"),
    "UPSTREAM_CONGESTION": ("Upstream Congestion", "Upstream channel utilization exceeds threshold"),
    "DOWNSTREAM_CONGESTION": ("Downstream Congestion", "Downstream channel utilization exceeds threshold"),
    "PLANT_DAMAGE": ("Plant Damage", "Physical damage to coaxial or fiber plant detected"),
    "CPE_MASS_OFFLINE": ("Mass CPE Offline", "Large number of modems offline simultaneously"),
    "SIGNAL_DEGRADATION": ("Signal Degradation", "RF signal quality below acceptable levels"),
    "TEMPERATURE_ALARM": ("Temperature Alarm", "Equipment temperature exceeds safe operating limits"),
    "CAPACITY_THRESHOLD": ("Capacity Threshold", "Node approaching maximum subscriber capacity"),
    "FIRMWARE_ISSUE": ("Firmware Issue", "Equipment firmware anomaly or update failure"),
    "RANGING_FAILURE": ("Ranging Failure", "High rate of modem ranging failures detected"),
    "MAINTENANCE_OVERRUN": ("Maintenance Overrun", "Maintenance window exceeded scheduled duration"),
    "GATING_FAILURE": ("Gating Signal Failure", "Maintenance gating check has failed"),
}

# ============================================
# Action Types (Cable Network)
# ============================================

ACTION_TYPES = [
    "MODEM_REMOTE_REBOOT",
    "FIRMWARE_PUSH",
    "PROVISIONING_REFRESH",
    "CMTS_PORT_RESET",
    "SIGNAL_LEVEL_ADJUSTMENT",
    "TRAFFIC_REROUTE",
    "NODE_CAPACITY_REBALANCE",
    "TICKET_CREATION",
]

ACTION_DESCRIPTIONS = {
    "MODEM_REMOTE_REBOOT": "Remotely reboot affected cable modems",
    "FIRMWARE_PUSH": "Push firmware update to affected equipment",
    "PROVISIONING_REFRESH": "Refresh modem provisioning configuration",
    "CMTS_PORT_RESET": "Reset CMTS upstream/downstream port",
    "SIGNAL_LEVEL_ADJUSTMENT": "Adjust RF signal levels on node or amplifier",
    "TRAFFIC_REROUTE": "Reroute traffic to alternate CMTS ports or paths",
    "NODE_CAPACITY_REBALANCE": "Rebalance subscriber load across node segments",
    "TICKET_CREATION": "Create trouble ticket for field technician dispatch",
}

ACTION_EFFECTIVENESS = {
    "MODEM_REMOTE_REBOOT": (70, 95),
    "FIRMWARE_PUSH": (60, 85),
    "PROVISIONING_REFRESH": (75, 95),
    "CMTS_PORT_RESET": (80, 100),
    "SIGNAL_LEVEL_ADJUSTMENT": (65, 90),
    "TRAFFIC_REROUTE": (70, 90),
    "NODE_CAPACITY_REBALANCE": (60, 85),
    "TICKET_CREATION": (50, 70),
}

# ============================================
# KPI Thresholds (Cable RF Metrics)
# ============================================

KPI_THRESHOLDS = {
    "ds_snr_db": {"critical": 30, "warning": 33, "healthy": 36},
    "us_snr_db": {"critical": 22, "warning": 25, "healthy": 28},
    "ds_power_level_dbmv": {
        "critical_low": -12, "warning_low": -8, "healthy_low": -6,
        "healthy_high": 6, "warning_high": 8, "critical_high": 12,
    },
    "us_power_level_dbmv": {
        "critical_low": 35, "warning_low": 38, "healthy_low": 40,
        "healthy_high": 48, "warning_high": 50, "critical_high": 52,
    },
    "latency_ms": {"critical": 100, "warning": 50, "healthy": 20},
    "packet_loss_percent": {"critical": 3.0, "warning": 1.0, "healthy": 0.5},
    "fec_uncorrected_rate": {"critical": 0.05, "warning": 0.01, "healthy": 0.001},
    "ds_channel_utilization": {"critical": 90, "warning": 75, "healthy": 50},
    "us_channel_utilization": {"critical": 85, "warning": 70, "healthy": 45},
    "node_cpu_utilization": {"critical": 95, "warning": 85, "healthy": 70},
    "node_memory_utilization": {"critical": 90, "warning": 80, "healthy": 65},
    "node_temperature": {"critical": 75, "warning": 65, "healthy": 50},
}

# Failure probabilities (per hour per node)
FAILURE_PROBABILITIES = {
    "NODE_OUTAGE": 0.001,
    "CMTS_CARD_FAILURE": 0.0005,
    "HIGH_NOISE_INGRESS": 0.02,
    "POWER_SUPPLY_FAILURE": 0.003,
    "AMPLIFIER_FAILURE": 0.005,
    "UPSTREAM_CONGESTION": 0.04,
    "DOWNSTREAM_CONGESTION": 0.03,
    "PLANT_DAMAGE": 0.002,
    "CPE_MASS_OFFLINE": 0.005,
    "SIGNAL_DEGRADATION": 0.01,
    "TEMPERATURE_ALARM": 0.008,
    "CAPACITY_THRESHOLD": 0.015,
    "FIRMWARE_ISSUE": 0.003,
    "RANGING_FAILURE": 0.01,
}

# ============================================
# Customer Data Constants
# ============================================

CUSTOMER_FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Daniel", "Lisa", "Matthew", "Nancy",
    "Anthony", "Betty", "Mark", "Margaret", "Steven", "Sandra", "Andrew", "Ashley",
    "Paul", "Dorothy", "Joshua", "Kimberly", "Kenneth", "Emily", "Kevin", "Donna",
]

CUSTOMER_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
]

STREET_NAMES = [
    "Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine St", "Elm Blvd",
    "Washington Ave", "Park Dr", "Lake Rd", "Hill Ct", "Valley Way", "Spring St",
    "Meadow Ln", "Sunset Blvd", "Forest Dr", "River Rd", "Church St", "School Rd",
    "Mill St", "Academy Dr", "Highland Ave", "Center St", "North Rd", "South Blvd",
    "Liberty St", "Union Ave", "Railroad Ave", "Market St", "Water St", "Bridge St",
    "Chestnut St", "Broad St", "Summit Ave", "College Dr", "Cherry Ln", "Walnut St",
]

SENTIMENT_TOPICS = [
    "internet_speed", "reliability", "price", "customer_service",
    "installation", "billing", "equipment", "outage", "wifi", "streaming",
]

SENTIMENT_SOURCES = ["nps_survey", "call_center", "social_media", "app_review", "chat"]

SENTIMENT_SOURCE_DISTRIBUTION = {
    "nps_survey": 0.30,
    "call_center": 0.25,
    "social_media": 0.20,
    "app_review": 0.15,
    "chat": 0.10,
}

# Trouble ticket categories
TICKET_CATEGORIES = ["service_outage", "slow_speed", "intermittent", "plant_damage", "noise_ingress"]
TICKET_PRIORITIES = ["P1", "P2", "P3", "P4"]
TICKET_STATUSES = ["open", "assigned", "in_progress", "resolved", "closed"]

TICKET_CATEGORY_DISTRIBUTION = {
    "service_outage": 0.20,
    "slow_speed": 0.30,
    "intermittent": 0.25,
    "plant_damage": 0.10,
    "noise_ingress": 0.15,
}

# ============================================
# Gating & Maintenance Constants
# ============================================

GATING_SIGNAL_TYPES = [
    "weather_check",
    "customer_impact_threshold",
    "concurrent_maintenance_limit",
    "resource_availability",
    "approval_required",
    "peak_hour_block",
    "conflict_check",
    "rollback_readiness",
]

MAINTENANCE_WINDOW_TYPES = ["planned_maintenance", "emergency", "upgrade", "plant_construction"]
MAINTENANCE_WINDOW_STATUSES = ["scheduled", "approved", "in_progress", "completed", "cancelled", "rescheduled"]

ECAF_CHANGE_TYPES = [
    "software_update", "hardware_replacement", "configuration_change",
    "plant_modification", "node_split", "cmts_migration",
]

ECAF_STATUSES = [
    "draft", "pending_review", "approved", "rejected",
    "executing", "completed", "rolled_back", "failed",
]

CONFLICT_TYPES = [
    "overlapping_time", "shared_node", "shared_headend",
    "shared_crew", "cascading_impact", "customer_impact_exceeded",
]

GATING_THRESHOLDS = {
    "max_concurrent_maintenance_per_headend": 3,
    "max_customer_impact_percent": 10.0,
    "peak_hours_start": 18,  # 6 PM
    "peak_hours_end": 23,    # 11 PM
    "wind_speed_limit_mph": 35,
    "temperature_min_f": 20,
    "temperature_max_f": 100,
    "min_crew_availability": 1,
    "max_reschedule_count": 3,
    "default_buffer_before_minutes": 30,
    "default_buffer_after_minutes": 30,
}

MAINTENANCE_REASONS = [
    "Routine preventive maintenance",
    "Node segmentation upgrade",
    "DOCSIS 3.1 to 4.0 upgrade",
    "Amplifier replacement",
    "Power supply replacement",
    "Fiber splice repair",
    "Coax cable replacement",
    "CMTS card replacement",
    "Firmware upgrade rollout",
    "Signal level optimization",
    "Noise ingress remediation",
    "Plant extension for new build",
    "Aerial to underground conversion",
    "Node split preparation",
]

# ============================================
# Dark NOC & AIOps Constants
# ============================================

AUTOMATION_LEVELS = {
    "L0_MANUAL": {
        "level": 0,
        "name": "Manual",
        "description": "All operations require human execution. AI provides no assistance.",
        "auto_resolve": False,
        "auto_suppress": False,
        "auto_correlate": False,
    },
    "L1_ASSISTED": {
        "level": 1,
        "name": "Assisted",
        "description": "AI recommends actions, humans execute all operations.",
        "auto_resolve": False,
        "auto_suppress": False,
        "auto_correlate": True,
    },
    "L2_PARTIAL": {
        "level": 2,
        "name": "Partial Automation",
        "description": "AI executes low-risk actions autonomously. Humans handle high-risk.",
        "auto_resolve": True,
        "auto_suppress": True,
        "auto_correlate": True,
        "max_risk": "low",
    },
    "L3_CONDITIONAL": {
        "level": 3,
        "name": "Conditional Automation",
        "description": "AI executes most actions unless human overrides. Escalates critical.",
        "auto_resolve": True,
        "auto_suppress": True,
        "auto_correlate": True,
        "max_risk": "medium",
    },
    "L4_HIGH": {
        "level": 4,
        "name": "High Automation",
        "description": "AI handles all except critical infrastructure changes.",
        "auto_resolve": True,
        "auto_suppress": True,
        "auto_correlate": True,
        "max_risk": "high",
    },
    "L5_FULL_AUTONOMY": {
        "level": 5,
        "name": "Full Autonomy (Dark NOC)",
        "description": "Fully autonomous operations. Humans monitor only.",
        "auto_resolve": True,
        "auto_suppress": True,
        "auto_correlate": True,
        "max_risk": "critical",
    },
}

AUTOMATION_POLICY_TYPES = [
    "auto_remediation",
    "auto_escalation",
    "auto_suppression",
    "auto_correlation",
    "predictive_action",
]

NOC_RUNBOOK_CATEGORIES = [
    "node_ops", "cmts_ops", "plant_ops",
    "customer_ops", "capacity_ops", "maintenance_ops",
]

ESCALATION_CRITERIA = {
    "risk_level_exceeds": "high",
    "confidence_below": 0.6,
    "customer_impact_above": 500,
    "repeated_failure_count": 3,
    "critical_infrastructure": True,
    "operator_override_recent": True,
    "financial_impact_above": 10000.0,
}

DEFAULT_DARK_NOC_CONFIG = {
    "initial_automation_level": "L2_PARTIAL",
    "initial_mode": "supervised",
    "human_escalation_threshold": 0.7,
    "max_autonomous_actions_per_hour": 50,
    "mandatory_human_review_types": ["NODE_OUTAGE", "CMTS_CARD_FAILURE", "PLANT_DAMAGE"],
    "alert_suppression_window_minutes": 5,
    "correlation_window_minutes": 5,
    "auto_disable_policy_threshold": 0.5,
    "cooldown_after_escalation_minutes": 15,
}

# ============================================
# Predictive Model Constants
# ============================================

PREDICTIVE_MODEL_TYPES = [
    "failure_prediction",
    "capacity_forecast",
    "churn_prediction",
    "degradation_forecast",
    "maintenance_need",
    "weather_impact",
    "sentiment_trend",
]

IMPACT_MODEL_SCENARIOS = [
    "node_failure",
    "cmts_failure",
    "headend_outage",
    "plant_damage",
    "maintenance_window",
    "capacity_overload",
    "weather_event",
]

CORRELATION_PATTERNS = {
    "temporal": {
        "window_minutes": 5,
        "description": "Alerts occurring within 5-minute window",
    },
    "spatial": {
        "same_node": True,
        "same_headend": True,
        "same_hub": True,
        "description": "Alerts from same network element or parent",
    },
    "causal": {
        "patterns": [
            {"cause": "POWER_SUPPLY_FAILURE", "effects": ["NODE_OUTAGE", "CPE_MASS_OFFLINE"]},
            {"cause": "PLANT_DAMAGE", "effects": ["SIGNAL_DEGRADATION", "CPE_MASS_OFFLINE", "NODE_OUTAGE"]},
            {"cause": "HIGH_NOISE_INGRESS", "effects": ["SIGNAL_DEGRADATION", "RANGING_FAILURE", "UPSTREAM_CONGESTION"]},
            {"cause": "CMTS_CARD_FAILURE", "effects": ["CPE_MASS_OFFLINE", "NODE_OUTAGE"]},
            {"cause": "AMPLIFIER_FAILURE", "effects": ["SIGNAL_DEGRADATION", "CPE_MASS_OFFLINE"]},
        ],
        "description": "Known cause-effect alert chains",
    },
    "topological": {
        "upstream_downstream": True,
        "description": "Alerts following network topology (headend->hub->node->amplifier)",
    },
}

# ============================================
# Geographic / Region Mapping
# ============================================

GEOGRAPHIC_REGIONS = [
    "Charlotte", "Dallas-Fort Worth", "Los Angeles", "Tampa Bay",
    "Columbus", "New York City", "Chicago", "Denver", "Atlanta", "Seattle",
    "Phoenix", "Minneapolis", "Miami", "Boston", "Portland",
    "Kansas City", "Nashville", "San Antonio", "Detroit", "Salt Lake City",
    "Toronto", "Vancouver", "Mexico City", "Sao Paulo", "Buenos Aires",
    "London", "Frankfurt", "Paris",
    "Dubai", "Cairo",
    "Mumbai", "Tokyo", "Seoul", "Singapore", "Jakarta",
    "Sydney", "Melbourne",
    "Lagos", "Johannesburg", "Nairobi",
]

CITY_TO_SERVICE_AREA = {}
for sa_name, sa_config in SERVICE_AREA_CONFIG.items():
    for city in sa_config["cities"]:
        CITY_TO_SERVICE_AREA[city] = sa_name

# City coordinates for node placement (approximate city centers)
CITY_COORDINATES = {
    # Charlotte (metro + outlying)
    "Charlotte": (35.2271, -80.8431), "Concord": (35.4088, -80.5795),
    "Gastonia": (35.2621, -81.1873), "Huntersville": (35.4107, -80.8429),
    "Mooresville": (35.5849, -80.8101), "Rock Hill": (34.9249, -81.0251),
    "Matthews": (35.1168, -80.7237), "Mint Hill": (35.1796, -80.6467),
    "Statesville": (35.7826, -80.8873), "Salisbury": (35.6710, -80.4742),
    "Monroe": (34.9854, -80.5495), "Indian Trail": (35.0768, -80.6693),
    "Waxhaw": (34.9243, -80.7434), "Kannapolis": (35.4874, -80.6217),
    # Dallas-Fort Worth (metro + outlying)
    "Dallas": (32.7767, -96.7970), "Fort Worth": (32.7555, -97.3308),
    "Arlington": (32.7357, -97.1081), "Plano": (33.0198, -96.6989),
    "Irving": (32.8140, -96.9489), "Garland": (32.9126, -96.6389),
    "Frisco": (33.1507, -96.8236), "McKinney": (33.1972, -96.6397),
    "Denton": (33.2148, -97.1331), "Richardson": (32.9483, -96.7299),
    "Waxahachie": (32.3866, -96.8483), "Weatherford": (32.7593, -97.7972),
    "Rockwall": (32.9312, -96.4597), "Mansfield": (32.5632, -97.1417),
    "Lewisville": (33.0462, -96.9942), "Corsicana": (32.0954, -96.4689),
    # Los Angeles (metro + outlying)
    "Los Angeles": (34.0522, -118.2437), "Long Beach": (33.7701, -118.1937),
    "Anaheim": (33.8366, -117.9143), "Santa Ana": (33.7455, -117.8677),
    "Glendale": (34.1425, -118.2551), "Pasadena": (34.1478, -118.1445),
    "Torrance": (33.8358, -118.3406), "Burbank": (34.1808, -118.3090),
    "Inglewood": (33.9617, -118.3531), "Downey": (33.9401, -118.1332),
    "Riverside": (33.9533, -117.3962), "Ontario": (34.0633, -117.6509),
    "Palmdale": (34.5794, -118.1165), "Santa Clarita": (34.3917, -118.5426),
    "Pomona": (34.0551, -117.7500), "Ventura": (34.2746, -119.2290),
    # Tampa Bay (metro + outlying)
    "Tampa": (27.9506, -82.4572), "St. Petersburg": (27.7676, -82.6403),
    "Clearwater": (27.9659, -82.8001), "Brandon": (27.9378, -82.2859),
    "Largo": (27.9095, -82.7873), "Palm Harbor": (28.0772, -82.7637),
    "Wesley Chapel": (28.2397, -82.3274), "Riverview": (27.8614, -82.3265),
    "Lakeland": (28.0395, -81.9498), "Bradenton": (27.4989, -82.5748),
    "Spring Hill": (28.4767, -82.5276), "New Port Richey": (28.2442, -82.7193),
    "Plant City": (28.0186, -82.1193), "Zephyrhills": (28.2336, -82.1812),
    # Columbus (metro + outlying)
    "Columbus": (39.9612, -82.9988), "Dublin": (40.0992, -83.1141),
    "Westerville": (40.1262, -82.9291), "Reynoldsburg": (39.9559, -82.8121),
    "Grove City": (39.8812, -83.0930), "Hilliard": (40.0334, -83.1585),
    "Gahanna": (40.0192, -82.8791), "Upper Arlington": (40.0275, -83.0624),
    "Zanesville": (39.9403, -82.0132), "Lancaster": (39.7137, -82.5993),
    "Delaware": (40.2987, -83.0680), "Marion": (40.5887, -83.1285),
    "Circleville": (39.6006, -82.9460), "Chillicothe": (39.3331, -82.9824),
    # New York City (metro + outlying)
    "Manhattan": (40.7831, -73.9712), "Brooklyn": (40.6782, -73.9442),
    "Queens": (40.7282, -73.7949), "Bronx": (40.8448, -73.8648),
    "Staten Island": (40.5795, -74.1502), "Yonkers": (40.9312, -73.8988),
    "New Rochelle": (40.9115, -73.7824), "White Plains": (41.0340, -73.7629),
    "Newark": (40.7357, -74.1724), "Jersey City": (40.7178, -74.0431),
    "Stamford": (41.0534, -73.5387), "Paterson": (40.9168, -74.1718),
    "Morristown": (40.7968, -74.4815), "Hempstead": (40.7062, -73.6187),
    "Huntington": (40.8682, -73.4257), "Middletown": (41.4459, -74.4229),
    # Chicago (metro + outlying)
    "Chicago": (41.8781, -87.6298), "Bolingbrook": (41.6986, -88.0684),
    "Naperville": (41.7508, -88.1535), "Joliet": (41.5250, -88.0817),
    "Elgin": (42.0354, -88.2826), "Schaumburg": (42.0334, -88.0834),
    "Evanston": (42.0451, -87.6877), "Oak Park": (41.8850, -87.7845),
    "Cicero": (41.8456, -87.7539), "Berwyn": (41.8506, -87.7937),
    "Waukegan": (42.3636, -87.8448), "DeKalb": (41.9295, -88.7503),
    "Kankakee": (41.1200, -87.8612), "Crystal Lake": (42.2411, -88.3162),
    "Plainfield": (41.6270, -88.2037), "Woodstock": (42.3147, -88.4487),
    # Denver (metro + outlying)
    "Denver": (39.7392, -104.9903), "Aurora": (39.7294, -104.8319),
    "Lakewood": (39.7047, -105.0814), "Thornton": (39.8680, -104.9719),
    "Arvada": (39.8028, -105.0875), "Westminster": (39.8367, -105.0372),
    "Centennial": (39.5681, -104.8686), "Boulder": (40.0150, -105.2705),
    "Littleton": (39.6133, -105.0166), "Broomfield": (39.9206, -105.0867),
    "Castle Rock": (39.3722, -104.8561), "Longmont": (40.1672, -105.1019),
    "Golden": (39.7555, -105.2211), "Parker": (39.5186, -104.7614),
    "Brighton": (39.9853, -104.8205), "Erie": (40.0503, -105.0500),
    # Atlanta (metro + outlying)
    "Atlanta": (33.7490, -84.3880), "Sandy Springs": (33.9304, -84.3733),
    "Roswell": (34.0232, -84.3616), "Johns Creek": (34.0289, -84.1984),
    "Alpharetta": (34.0754, -84.2941), "Marietta": (33.9526, -84.5499),
    "Smyrna": (33.8839, -84.5144), "Brookhaven": (33.8651, -84.3365),
    "Dunwoody": (33.9462, -84.3346), "Kennesaw": (34.0234, -84.6155),
    "Cartersville": (34.1651, -84.7999), "Newnan": (33.3807, -84.7997),
    "Covington": (33.5968, -83.8602), "McDonough": (33.4473, -84.1469),
    "Peachtree City": (33.3968, -84.5957), "Canton": (34.2368, -84.4908),
    # Seattle (metro + outlying)
    "Seattle": (47.6062, -122.3321), "Bellevue": (47.6101, -122.2015),
    "Tacoma": (47.2529, -122.4443), "Kent": (47.3809, -122.2348),
    "Renton": (47.4829, -122.2171), "Federal Way": (47.3223, -122.3126),
    "Kirkland": (47.6815, -122.2087), "Redmond": (47.6740, -122.1215),
    "Bothell": (47.7623, -122.2054), "Lynnwood": (47.8207, -122.3151),
    "Everett": (47.9790, -122.2021), "Olympia": (47.0379, -122.9007),
    "Puyallup": (47.1854, -122.2929), "Bremerton": (47.5673, -122.6326),
    "Snohomish": (47.9129, -122.0990), "Auburn": (47.3073, -122.2285),
    # Phoenix (metro + outlying)
    "Phoenix": (33.4484, -112.0740), "Mesa": (33.4152, -111.8315),
    "Chandler": (33.3062, -111.8413), "Scottsdale": (33.4942, -111.9261),
    "Gilbert": (33.3528, -111.7890), "Tempe": (33.4255, -111.9400),
    "Avondale": (33.4356, -112.3496), "Peoria": (33.5806, -112.2374),
    "Surprise": (33.6292, -112.3322), "Buckeye": (33.3703, -112.5838),
    "Apache Junction": (33.4150, -111.5496), "Casa Grande": (32.8795, -111.7574),
    "Maricopa": (33.0581, -112.0476), "Fountain Hills": (33.6117, -111.7174),
    # Minneapolis (metro + outlying)
    "Minneapolis": (44.9778, -93.2650), "St. Paul": (44.9537, -93.0900),
    "Bloomington": (44.8408, -93.2983), "Plymouth": (45.0105, -93.4555),
    "Brooklyn Park": (45.0941, -93.3563), "Maple Grove": (45.0724, -93.4558),
    "Eagan": (44.8041, -93.1669), "Eden Prairie": (44.8547, -93.4708),
    "Stillwater": (45.0564, -92.8313), "Woodbury": (44.9239, -92.9594),
    "Lakeville": (44.6497, -93.2427), "Shakopee": (44.7980, -93.5269),
    "Burnsville": (44.7677, -93.2777), "Chaska": (44.7894, -93.6022),
    # Miami (metro + outlying)
    "Miami": (25.7617, -80.1918), "Fort Lauderdale": (26.1224, -80.1373),
    "Hollywood": (26.0112, -80.1495), "Hialeah": (25.8576, -80.2781),
    "Coral Springs": (26.2712, -80.2706), "Pembroke Pines": (26.0031, -80.2241),
    "Miramar": (25.9860, -80.2323), "Davie": (26.0765, -80.2521),
    "Boca Raton": (26.3683, -80.1289), "Homestead": (25.4687, -80.4776),
    "Delray Beach": (26.4615, -80.0728), "Jupiter": (26.9342, -80.0942),
    "Deerfield Beach": (26.3184, -80.0998), "Cutler Bay": (25.5808, -80.3467),
    # Boston (metro + outlying)
    "Boston": (42.3601, -71.0589), "Cambridge": (42.3736, -71.1097),
    "Quincy": (42.2529, -71.0023), "Newton": (42.3370, -71.2092),
    "Somerville": (42.3876, -71.0995), "Brookline": (42.3318, -71.1212),
    "Waltham": (42.3765, -71.2356), "Medford": (42.4184, -71.1062),
    "Lowell": (42.6334, -71.3162), "Brockton": (42.0834, -71.0184),
    "Gloucester": (42.6159, -70.6620), "Framingham": (42.2793, -71.4162),
    "Peabody": (42.5279, -70.9287), "Woburn": (42.4793, -71.1523),
    # Portland (metro + outlying)
    "Portland": (45.5152, -122.6784), "Beaverton": (45.4871, -122.8037),
    "Hillsboro": (45.5229, -122.9898), "Gresham": (45.4983, -122.4310),
    "Lake Oswego": (45.4207, -122.6706), "Tigard": (45.4312, -122.7715),
    "Tualatin": (45.3838, -122.7637), "Oregon City": (45.3573, -122.6068),
    "McMinnville": (45.2101, -123.1968), "Wilsonville": (45.2998, -122.7735),
    "Canby": (45.2629, -122.6926), "Newberg": (45.3001, -122.9731),
    "Woodburn": (45.1437, -122.8554), "Milwaukie": (45.4429, -122.6387),
    # Kansas City (metro + outlying)
    "Kansas City": (39.0997, -94.5786), "Overland Park": (38.9822, -94.6708),
    "Olathe": (38.8814, -94.8191), "Independence": (39.0911, -94.4155),
    "Lee's Summit": (38.9108, -94.3822), "Shawnee": (39.0417, -94.7202),
    "Blue Springs": (39.0169, -94.2816), "Lenexa": (38.9536, -94.7336),
    "Liberty": (39.2461, -94.4191), "Lawrence": (38.9717, -95.2353),
    "Leavenworth": (39.3114, -94.9224), "Belton": (38.8119, -94.5322),
    "Bonner Springs": (39.0597, -94.8833), "Grain Valley": (39.0153, -94.1986),
    # Nashville (metro + outlying)
    "Nashville": (36.1627, -86.7816), "Murfreesboro": (35.8456, -86.3903),
    "Franklin": (35.9251, -86.8689), "Hendersonville": (36.3048, -86.6200),
    "Gallatin": (36.3884, -86.4467), "Mount Juliet": (36.2001, -86.5186),
    "Lebanon": (36.2081, -86.2911), "Brentwood": (36.0331, -86.7828),
    "Clarksville": (36.5298, -87.3595), "Dickson": (36.0770, -87.3878),
    "Columbia": (35.6151, -87.0353), "Springfield": (36.5092, -86.8850),
    "Shelbyville": (35.4834, -86.4603), "Nolensville": (35.9523, -86.6694),
    # San Antonio (metro + outlying)
    "San Antonio": (29.4241, -98.4936), "New Braunfels": (29.7030, -98.1245),
    "San Marcos": (29.8833, -97.9414), "Schertz": (29.5522, -98.2697),
    "Cibolo": (29.5727, -98.2269), "Converse": (29.5177, -98.3164),
    "Universal City": (29.5480, -98.2911), "Live Oak": (29.5647, -98.3378),
    "Seguin": (29.5688, -97.9647), "Boerne": (29.7947, -98.7320),
    "Floresville": (29.1335, -98.1564), "Castroville": (29.3558, -98.8789),
    "Pleasanton": (28.9672, -98.4789), "Hondo": (29.3474, -99.1414),
    # Detroit (metro + outlying)
    "Detroit": (42.3314, -83.0458), "Warren": (42.5145, -83.0147),
    "Sterling Heights": (42.5803, -83.0302), "Dearborn": (42.3223, -83.1763),
    "Livonia": (42.3684, -83.3527), "Troy": (42.6064, -83.1498),
    "Southfield": (42.4734, -83.2219), "Royal Oak": (42.4895, -83.1446),
    "Ann Arbor": (42.2808, -83.7430), "Pontiac": (42.6389, -83.2910),
    "Novi": (42.4806, -83.4755), "Westland": (42.3242, -83.4002),
    "Ypsilanti": (42.2411, -83.6130), "Howell": (42.6072, -83.9294),
    # Salt Lake City (metro + outlying)
    "Salt Lake City": (40.7608, -111.8910), "West Valley City": (40.6916, -112.0011),
    "Provo": (40.2338, -111.6585), "Sandy": (40.5650, -111.8590),
    "Orem": (40.2969, -111.6946), "Ogden": (41.2230, -111.9738),
    "West Jordan": (40.6097, -111.9391), "Layton": (41.0602, -111.9711),
    "Park City": (40.6461, -111.4980), "Tooele": (40.5308, -112.2983),
    "American Fork": (40.3769, -111.7957), "Lehi": (40.3916, -111.8508),
    "Bountiful": (40.8894, -111.8808), "Draper": (40.5247, -111.8638),
    # Toronto (metro + outlying)
    "Toronto": (43.6532, -79.3832), "Mississauga": (43.5890, -79.6441),
    "Brampton": (43.7315, -79.7624), "Markham": (43.8561, -79.3370),
    "Vaughan": (43.8361, -79.4981), "Richmond Hill": (43.8828, -79.4403),
    "Oakville": (43.4675, -79.6877), "Burlington": (43.3255, -79.7990),
    "Pickering": (43.8354, -79.0868), "Ajax": (43.8509, -79.0204),
    "Whitby": (43.8975, -78.9429), "Oshawa": (43.8971, -78.8658),
    "Milton": (43.5183, -79.8774), "Georgetown": (43.6527, -79.9235),
    # Mexico City (metro + outlying)
    "Mexico City": (19.4326, -99.1332), "Ecatepec": (19.6013, -99.0498),
    "Naucalpan": (19.4784, -99.2398), "Tlalnepantla": (19.5370, -99.1948),
    "Coacalco": (19.6284, -99.1014), "Tultitlan": (19.6456, -99.1677),
    "Atizapan": (19.5578, -99.2587), "Cuautitlan": (19.6726, -99.1774),
    "Texcoco": (19.5152, -98.8823), "Chalco": (19.2629, -98.8976),
    "Ixtapaluca": (19.3192, -98.8828), "Huixquilucan": (19.3640, -99.3514),
    # Sao Paulo (metro + outlying)
    "Sao Paulo": (-23.5505, -46.6333), "Guarulhos": (-23.4538, -46.5333),
    "Campinas": (-22.9099, -47.0626), "Santo Andre": (-23.6737, -46.5432),
    "Osasco": (-23.5325, -46.7917), "Sorocaba": (-23.5015, -47.4526),
    "Barueri": (-23.5114, -46.8761), "Diadema": (-23.6861, -46.6228),
    "Jundiai": (-23.1857, -46.8978), "Mogi das Cruzes": (-23.5227, -46.1858),
    "Carapicuiba": (-23.5225, -46.8356), "Suzano": (-23.5424, -46.3106),
    # London (metro + outlying)
    "London": (51.5074, -0.1278), "Reading": (51.4543, -0.9781),
    "Croydon": (51.3762, -0.0982), "Watford": (51.6565, -0.3973),
    "Slough": (51.5105, -0.5950), "Guildford": (51.2365, -0.5703),
    "Dartford": (51.4463, 0.2146), "Bromley": (51.4039, 0.0198),
    "Enfield": (51.6522, -0.0808), "Harrow": (51.5898, -0.3346),
    "Romford": (51.5745, 0.1827), "Kingston": (51.4123, -0.3007),
    "Epsom": (51.3360, -0.2686), "Luton": (51.8787, -0.4200),
    # Frankfurt (metro + outlying)
    "Frankfurt": (50.1109, 8.6821), "Wiesbaden": (50.0782, 8.2398),
    "Darmstadt": (49.8728, 8.6512), "Offenbach": (50.1005, 8.7648),
    "Mainz": (49.9929, 8.2473), "Hanau": (50.1267, 8.9169),
    "Bad Homburg": (50.2268, 8.6184), "Friedberg": (50.3348, 8.7560),
    "Ruesselsheim": (49.9896, 8.4113), "Oberursel": (50.2020, 8.5778),
    "Giessen": (50.5840, 8.6784), "Marburg": (50.8095, 8.7710),
    # Dubai (metro + outlying)
    "Dubai": (25.2048, 55.2708), "Abu Dhabi": (24.4539, 54.3773),
    "Sharjah": (25.3463, 55.4209), "Ajman": (25.4111, 55.4354),
    "Al Ain": (24.1917, 55.7606), "Ras Al Khaimah": (25.7895, 55.9432),
    "Fujairah": (25.1288, 56.3264), "Umm Al Quwain": (25.5647, 55.5553),
    "Khor Fakkan": (25.3401, 56.3490), "Dibba Al Fujairah": (25.5942, 56.2628),
    "Kalba": (25.0667, 56.3556), "Madinat Zayed": (23.6551, 53.7070),
    # Mumbai (metro + outlying)
    "Mumbai": (19.0760, 72.8777), "Thane": (19.2183, 72.9781),
    "Navi Mumbai": (19.0330, 73.0297), "Kalyan": (19.2437, 73.1355),
    "Vasai": (19.3919, 72.8397), "Panvel": (18.9894, 73.1175),
    "Bhiwandi": (19.2967, 73.0631), "Mira Bhayandar": (19.2952, 72.8544),
    "Ulhasnagar": (19.2215, 73.1645), "Ambernath": (19.1938, 73.1856),
    "Badlapur": (19.1570, 73.2285), "Alibaug": (18.6484, 72.8723),
    # Tokyo (metro + outlying)
    "Tokyo": (35.6762, 139.6503), "Yokohama": (35.4437, 139.6380),
    "Kawasaki": (35.5308, 139.7030), "Saitama": (35.8617, 139.6455),
    "Chiba": (35.6073, 140.1063), "Sagamihara": (35.5714, 139.3733),
    "Hachioji": (35.6564, 139.3238), "Machida": (35.5488, 139.4451),
    "Fuchu": (35.6693, 139.4777), "Tachikawa": (35.6942, 139.4073),
    "Musashino": (35.7177, 139.5661), "Mitaka": (35.6836, 139.5593),
    # Singapore (city-state)
    "Singapore": (1.3521, 103.8198), "Jurong East": (1.3329, 103.7436),
    "Tampines": (1.3496, 103.9568), "Woodlands": (1.4382, 103.7891),
    "Ang Mo Kio": (1.3691, 103.8454), "Bedok": (1.3236, 103.9273),
    "Clementi": (1.3162, 103.7649), "Bukit Batok": (1.3490, 103.7496),
    "Sengkang": (1.3868, 103.8914), "Punggol": (1.4018, 103.9090),
    "Yishun": (1.4304, 103.8354), "Hougang": (1.3612, 103.8863),
    # Sydney (metro + outlying)
    "Sydney": (-33.8688, 151.2093), "Parramatta": (-33.8150, 151.0011),
    "Penrith": (-33.7507, 150.6942), "Liverpool": (-33.9210, 150.9237),
    "Campbelltown": (-34.0650, 150.8142), "Blacktown": (-33.7688, 150.9057),
    "Hornsby": (-33.7054, 151.0986), "Manly": (-33.7970, 151.2878),
    "Bankstown": (-33.9175, 151.0352), "Sutherland": (-34.0315, 151.0571),
    "Ryde": (-33.8132, 151.1013), "Chatswood": (-33.7969, 151.1832),
    # Vancouver (metro + outlying)
    "Vancouver": (49.2827, -123.1207), "Surrey": (49.1913, -122.8490),
    "Burnaby": (49.2488, -122.9805), "Richmond": (49.1666, -123.1336),
    "Coquitlam": (49.2838, -122.7932), "Delta": (49.0847, -123.0587),
    "Langley": (49.1044, -122.6615), "Abbotsford": (49.0504, -122.3045),
    "North Vancouver": (49.3200, -123.0724), "New Westminster": (49.2057, -122.9110),
    "Chilliwack": (49.1579, -121.9514), "Squamish": (49.7016, -123.1559),
    # Buenos Aires (metro + outlying)
    "Buenos Aires": (-34.6037, -58.3816), "La Plata": (-34.9205, -57.9536),
    "Quilmes": (-34.7203, -58.2524), "Lomas de Zamora": (-34.7617, -58.3989),
    "Lanus": (-34.7006, -58.3927), "Avellaneda": (-34.6621, -58.3653),
    "San Isidro": (-34.4708, -58.5299), "Tigre": (-34.4260, -58.5797),
    "Pilar": (-34.4588, -58.9142), "Moreno": (-34.6534, -58.7898),
    "Merlo": (-34.6662, -58.7279), "San Martin": (-34.5753, -58.5353),
    # Paris (metro + outlying)
    "Paris": (48.8566, 2.3522), "Versailles": (48.8014, 2.1301),
    "Boulogne-Billancourt": (48.8352, 2.2409), "Saint-Denis": (48.9362, 2.3574),
    "Montreuil": (48.8611, 2.4436), "Nanterre": (48.8922, 2.2069),
    "Creteil": (48.7904, 2.4555), "Argenteuil": (48.9472, 2.2467),
    "Meaux": (48.9604, 2.8791), "Evry": (48.6344, 2.4407),
    "Pontoise": (49.0501, 2.1003), "Melun": (48.5391, 2.6559),
    # Seoul (metro + outlying)
    "Seoul": (37.5665, 126.9780), "Incheon": (37.4563, 126.7052),
    "Suwon": (37.2636, 127.0286), "Seongnam": (37.4201, 127.1265),
    "Goyang": (37.6584, 126.8320), "Yongin": (37.2411, 127.1776),
    "Bucheon": (37.5034, 126.7660), "Ansan": (37.3219, 126.8309),
    "Anyang": (37.3943, 126.9568), "Uijeongbu": (37.7381, 127.0338),
    "Gwangmyeong": (37.4786, 126.8648), "Siheung": (37.3800, 126.8030),
    # Jakarta (metro + outlying)
    "Jakarta": (-6.2088, 106.8456), "Bogor": (-6.5971, 106.8060),
    "Depok": (-6.4025, 106.7942), "Tangerang": (-6.1702, 106.6403),
    "Bekasi": (-6.2383, 106.9756), "South Tangerang": (-6.2894, 106.7108),
    "Cikarang": (-6.3195, 107.1525), "Cibinong": (-6.4818, 106.8513),
    "Serpong": (-6.3143, 106.6638), "Karawang": (-6.3227, 107.3376),
    "Cilegon": (-6.0023, 106.0522), "Serang": (-6.1200, 106.1503),
    # Melbourne (metro + outlying)
    "Melbourne": (-37.8136, 144.9631), "Geelong": (-38.1499, 144.3617),
    "Ballarat": (-37.5622, 143.8503), "Dandenong": (-37.9871, 145.2149),
    "Frankston": (-38.1437, 145.1219), "Werribee": (-37.9017, 144.6593),
    "Sunbury": (-37.5771, 144.7262), "Melton": (-37.6847, 144.5713),
    "Cranbourne": (-38.0997, 145.2834), "Pakenham": (-38.0711, 145.4873),
    "Berwick": (-38.0330, 145.3556), "Mornington": (-38.2182, 145.0378),
    # Cairo (metro + outlying)
    "Cairo": (30.0444, 31.2357), "Giza": (30.0131, 31.2089),
    "Helwan": (29.8425, 31.3345), "Nasr City": (30.0626, 31.3395),
    "Maadi": (29.9602, 31.2502), "Heliopolis": (30.0912, 31.3232),
    "October City": (29.9609, 30.9179), "Shubra": (30.1262, 31.2422),
    "Obour": (30.2281, 31.4522), "New Cairo": (30.0196, 31.4637),
    "Badr": (30.1283, 31.7238), "Shorouk": (30.1571, 31.6098),
    # Lagos (metro + outlying)
    "Lagos Island": (6.4541, 3.3947), "Ikeja": (6.6018, 3.3515),
    "Lekki": (6.4698, 3.5852), "Victoria Island": (6.4281, 3.4219),
    "Surulere": (6.5031, 3.3491), "Mushin": (6.5340, 3.3544),
    "Ikorodu": (6.6194, 3.5105), "Badagry": (6.4163, 2.8810),
    "Epe": (6.5847, 3.9836), "Ajah": (6.4671, 3.5702),
    "Agege": (6.6211, 3.3278), "Oshodi": (6.5542, 3.3407),
    # Johannesburg (metro + outlying)
    "Johannesburg": (-26.2041, 28.0473), "Pretoria": (-25.7479, 28.2293),
    "Sandton": (-26.1076, 28.0567), "Soweto": (-26.2678, 27.8585),
    "Centurion": (-25.8603, 28.1894), "Midrand": (-25.9867, 28.1273),
    "Randburg": (-26.0935, 28.0006), "Roodepoort": (-26.1622, 27.8727),
    "Germiston": (-26.2227, 28.1674), "Benoni": (-26.1854, 28.3205),
    "Boksburg": (-26.2120, 28.2604), "Kempton Park": (-26.1001, 28.2326),
    # Nairobi (metro + outlying)
    "Nairobi CBD": (-1.2864, 36.8172), "Thika": (-1.0396, 37.0900),
    "Kiambu": (-1.1714, 36.8356), "Machakos": (-1.5177, 37.2634),
    "Ruiru": (-1.1449, 36.9604), "Juja": (-1.1025, 37.0136),
    "Kitengela": (-1.4703, 36.9558), "Athi River": (-1.4582, 36.9809),
    "Limuru": (-1.1095, 36.6460), "Ngong": (-1.3610, 36.6567),
    "Karuri": (-1.1620, 36.7086), "Kikuyu": (-1.2464, 36.6817),
}

# ============================================
# Weather Impact Constants (Cable Plant)
# ============================================

WEATHER_CONDITIONS = [
    "Clear", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain",
    "Thunderstorm", "Snow", "Ice Storm", "Fog", "High Wind",
    "Extreme Heat", "Extreme Cold",
]

WEATHER_IMPACT_ON_PLANT = {
    "Clear": {"impact": 0.0, "aerial_risk": "none", "pedestal_risk": "none"},
    "Partly Cloudy": {"impact": 0.0, "aerial_risk": "none", "pedestal_risk": "none"},
    "Cloudy": {"impact": 0.0, "aerial_risk": "none", "pedestal_risk": "none"},
    "Light Rain": {"impact": 0.1, "aerial_risk": "low", "pedestal_risk": "low"},
    "Heavy Rain": {"impact": 0.4, "aerial_risk": "medium", "pedestal_risk": "medium"},
    "Thunderstorm": {"impact": 0.6, "aerial_risk": "high", "pedestal_risk": "medium"},
    "Snow": {"impact": 0.3, "aerial_risk": "medium", "pedestal_risk": "low"},
    "Ice Storm": {"impact": 0.8, "aerial_risk": "critical", "pedestal_risk": "medium"},
    "Fog": {"impact": 0.05, "aerial_risk": "none", "pedestal_risk": "none"},
    "High Wind": {"impact": 0.5, "aerial_risk": "high", "pedestal_risk": "low"},
    "Extreme Heat": {"impact": 0.4, "aerial_risk": "medium", "pedestal_risk": "medium"},
    "Extreme Cold": {"impact": 0.3, "aerial_risk": "medium", "pedestal_risk": "low"},
}

# ============================================
# Crew & Dispatch Constants
# ============================================

CREW_TYPES = {
    "line_tech": {"skill_level": "L1", "description": "Line technician - coax/aerial work"},
    "headend_tech": {"skill_level": "L2", "description": "Headend technician - CMTS/equipment"},
    "fiber_tech": {"skill_level": "L2", "description": "Fiber splicer/technician"},
    "senior_engineer": {"skill_level": "L3", "description": "Senior RF/network engineer"},
}

EQUIPMENT_FOR_TICKET = {
    "service_outage": ["signal_meter", "tone_generator", "splitter", "connector_kit"],
    "slow_speed": ["signal_meter", "modem_tester", "laptop"],
    "intermittent": ["signal_meter", "spectrum_analyzer", "connector_kit", "tap_wrench"],
    "plant_damage": ["hard_hat", "bucket_truck", "cable_reel", "splice_kit", "connector_kit"],
    "noise_ingress": ["spectrum_analyzer", "signal_meter", "trap_filter", "connector_kit", "noise_sniffer"],
}

# ============================================
# System Defaults
# ============================================

DEFAULT_NODE_STATUS_DISTRIBUTION = {
    "operational": 0.85,
    "degraded": 0.10,
    "maintenance": 0.04,
    "failed": 0.01,
}

DEFAULT_AMPLIFIER_TYPES = ["trunk", "bridger", "line_extender", "distribution"]

AMPLIFIER_TYPE_DISTRIBUTION = {
    "trunk": 0.20,
    "bridger": 0.25,
    "line_extender": 0.35,
    "distribution": 0.20,
}

AMPLIFIER_LOCATION_DISTRIBUTION = {
    "aerial": 0.60,
    "pedestal": 0.30,
    "underground": 0.10,
}

# Operator names for simulation
OPERATOR_NAMES = [
    "Mike Torres", "Sarah Chen", "David Kim", "Emily Watson",
    "Carlos Rivera", "Amanda Foster", "James O'Brien", "Lisa Patel",
    "Robert Chang", "Nicole Adams", "Marcus Johnson", "Rachel Lee",
]

# ============================================
# Capacity Planning Constants
# ============================================

UPGRADE_PATHS = {
    "docsis_3.0_to_3.1": {
        "description": "DOCSIS 3.0 to 3.1 upgrade",
        "estimated_cost_per_node": 5000,
        "bandwidth_improvement_percent": 200,
        "timeline_days_per_node": 2,
    },
    "docsis_3.1_to_4.0": {
        "description": "DOCSIS 3.1 to 4.0 upgrade",
        "estimated_cost_per_node": 12000,
        "bandwidth_improvement_percent": 400,
        "timeline_days_per_node": 3,
    },
    "node_split": {
        "description": "Split existing node into 2+ segments",
        "estimated_cost_per_split": 25000,
        "capacity_improvement_percent": 100,
        "timeline_days": 14,
    },
    "cmts_expansion": {
        "description": "Add CMTS ports or new chassis",
        "estimated_cost_per_chassis": 150000,
        "port_capacity_increase": 96,
        "timeline_days": 30,
    },
    "fttp_migration": {
        "description": "Fiber to the Premises migration",
        "estimated_cost_per_home": 1200,
        "bandwidth_improvement_percent": 1000,
        "timeline_months": 18,
    },
}
