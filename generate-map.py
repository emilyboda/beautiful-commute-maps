import json
from shapely.geometry import shape, GeometryCollection, Point
import googlemaps
from datetime import datetime
import time

######################################
######## Instructions ################
######################################
# 1. Set the following:
path_to_folder = "/maps/"

# 2. Go to geojson.io and create a polygon shape that contains 
#   the bounds where you would like to look for a place to live.
#   Click "save" and name it "bounds.geojson" and place it in the folder
path_to_bounds = path_to_folder+"bounds.geojson"

# 3. Set your resolution
#   1.0 is recommended as min for driving
#   0.5 is recommended as a max for bicycling
#   0.2 is recommended as max for public transit
resolution = 0.2 # miles between points

# 4. Set the API key
api_key = "INSERT YOUR API KEY HERE" 

# 5. Set your commute-to location
#   coords = [lon,lat] Make sure there is no space between the coords!
work = [-75.1567,39.9583] # Iffy Books in Philadelphia

# 6. Set your transit type
#   options: driving, walking, transit, bicycling
transit_type = 'transit'

# 7. Set your future communte date/time
#   I usually use a future Monday at 9 am (that is not a holiday)
#   You cannot use a past date so make sure to double check this
set_arrival_time = datetime(2022,12,12,8,30)

# Other
cost = 0.004

######### IMPORT BOUNDS
with open(path_to_bounds, 'r') as f:
    js = json.load(f)

######### FIND SQUARE BOUNDS
# Goes through every coordinate in bounds and finds 
# the furthest north, east, south, and west points
lowercorner = [500., 500.]
uppercorner = [-500., -500.]
for feature in js['features']:
    polygon = shape(feature['geometry'])
    if polygon.bounds[0] < lowercorner[0]:
        lowercorner[0] = polygon.bounds[0]
    if polygon.bounds[1] < lowercorner[1]:
        lowercorner[1] = polygon.bounds[1]
    if polygon.bounds[2] > uppercorner[0]:
        uppercorner[0] = polygon.bounds[2]
    if polygon.bounds[3] > uppercorner[1]:
        uppercorner[1] = polygon.bounds[3]

########## CREATE GEOJSON
conversion_lat = 69.00 # 1 point in lat/lon = X miles in lat/lon
conversion_lon = 53.06 # 1 point in lat/lon = X miles in lat/lon
conversion = [53.06, 69.00]

currentpoint = [lowercorner[0], lowercorner[1]]

inpoints = {
  "type": "FeatureCollection",
  "features": []
}

outpoints = {
  "type": "FeatureCollection",
  "features": []
}

while currentpoint[0] < uppercorner[0]:
    while currentpoint[1] < uppercorner[1]:
        for feature in js['features']:
            polygon = shape(feature['geometry'])
            if polygon.contains(Point(currentpoint[0], currentpoint[1])):
                inpoints['features'].append(
                    {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [currentpoint[0],currentpoint[1]]
                            }
                        }
                )
            else:
                outpoints['features'].append(
                {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [currentpoint[0],currentpoint[1]]
                        }
                    }
            )
        currentpoint[1] = currentpoint[1] + resolution/conversion[1]
    currentpoint[1] = lowercorner[1]*1. 
    currentpoint[0] = currentpoint[0] + resolution/conversion[0]

print('found', len(inpoints['features']), 'points out of', len(inpoints['features'])+len(outpoints['features']),'to process at', resolution, 'miles btwn points')
print('this will cost', len(inpoints['features'])*cost, 'USD')

with open(path_to_folder+"inpoints.geojson", 'w') as outfile:
    json.dump(inpoints,outfile)
with open(path_to_folder+"outpoints.geojson", 'w') as outfile:
    json.dump(outpoints,outfile)

continue_question = str(input('Do you want to continue (y) or use existing points (n)? '))

if continue_question == 'y':
    ######## GET COMMUTE TIME
    gmaps = googlemaps.Client(key=api_key)
    counter = 1
    points_array = []
    for feature in inpoints['features']:
        point = feature['geometry']['coordinates']
        if counter%20 == 0 or feature == inpoints['features'][-1]:
            points_array.append(str(point[1])+","+str(point[0]))
            distance_result = gmaps.distance_matrix(points_array,
                                                str(work[1])+","+str(work[0]),
                                                mode=transit_type,
                                                arrival_time=set_arrival_time
                                            )
            for row in range(len(distance_result['rows'])):
                results = distance_result['rows'][row]['elements'][0]
                if results['status'] == 'OK':
                    print('found results')
                    inpoints['features'][counter-1-(len(points_array)-row-1)]['properties']['distance'] = results['distance']['value']/1000.
                    inpoints['features'][counter-1-(len(points_array)-row-1)]['properties']['duration'] = results['duration']['value']/60.
                    inpoints['features'][counter-1-(len(points_array)-row-1)]['properties']['address'] = distance_result['origin_addresses'][row]
                elif results['status'] == 'ZERO_RESULTS':
                    print('no results')
                    inpoints['features'][counter-1-(len(points_array)-row-1)]['properties']['distance'] = 10000.
                    inpoints['features'][counter-1-(len(points_array)-row-1)]['properties']['duration'] = 10000.
                    inpoints['features'][counter-1-(len(points_array)-row-1)]['properties']['address'] = distance_result['origin_addresses'][row]
            points_array = []
            print('result ',counter, '/', len(inpoints['features']), 'at cost', counter*cost)
            with open(path_to_folder+"points-for-plotting.geojson", 'w') as outfile:
                json.dump(inpoints,outfile)
        elif counter%20 != 0:
            points_array.append(str(point[1])+","+str(point[0]))
        if counter % 100 == 0:
            time.sleep(1)
        counter = counter + 1

    with open(path_to_folder+"points-for-plotting.geojson", 'w') as outfile:
        json.dump(inpoints,outfile)

elif continue_question == 'n':
    with open(path_to_folder+"points-for-plotting.geojson",'r') as f:
        inpoints = json.load(f)

spoints = {
  "type": "FeatureCollection",
  "features": []
}
for feature in inpoints['features']:
    coord = feature['geometry']['coordinates']
    newfeature = {
                            "type": "Feature",
                            "properties": feature['properties'],
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [[[coord[0]-0.5*resolution/conversion[0], coord[1]-0.5*resolution/conversion[1]],
                                                [coord[0]-0.5*resolution/conversion[0], coord[1]+0.5*resolution/conversion[1]],
                                                [coord[0]+0.5*resolution/conversion[0], coord[1]+0.5*resolution/conversion[1]],
                                                [coord[0]+0.5*resolution/conversion[0], coord[1]-0.5*resolution/conversion[1]],
                                                [coord[0]-0.5*resolution/conversion[0], coord[1]-0.5*resolution/conversion[1]]
                                ]]
                            }
                        }
    
    newfeature['properties']['point'] = [feature['geometry']['coordinates'][1],feature['geometry']['coordinates'][0]]
    spoints['features'].append(newfeature)

with open(path_to_folder+"rectanges-for-plotting.geojson", 'w') as outfile:
        json.dump(spoints,outfile)
print('saved in', path_to_folder+"rectangles-for-plotting.geojson")
