import operator
import re
import math
from http import HTTPStatus

from flask import Flask, jsonify, request

app = Flask(__name__)

robot_regex = re.compile(r"robot#([1-9][0-9]*)")
variables = {
    'robots': {},
    'aliens': {}
}


class MyException(Exception):
    def __init__(self, arg1, arg2=None):
        self.arg1 = arg1
        self.arg2 = arg2
        super(MyException, self).__init__(arg1)


class Point:
    def __init__(self, position):
        self.X = None
        self.Y = None
        if(('x' in position) and ('y' in position)):
            self.X = position['x']
            self.Y = position['y']
        else:
            if('south' in position):
                self.Y = position['south'] * -1
            if('north' in position):
                self.Y = position['north']
            if('west' in position):
                self.X = position['west'] * -1
            if('east' in position):
                self.X = position['east']

        if((self.X == None) or (self.Y == None)):
            raise MyException('400')

    def distance(self, p, metric='euclidean'):
        if(metric == 'euclidean'):
            return math.hypot(self.X - p.X, self.Y - p.Y)
        else:
            return abs(self.X - p.X) + abs(self.Y - p.Y)

    def to_object(self):
        return {
            'x': self.X,
            'y': self.Y
        }

    def find_nearest(self, length=1):

        arr = []
        for k, v in variables['robots'].items():
            arr.append((self.distance(v), int(k)))

        arr.sort()

        ans = []
        for i in range(min(len(arr), length)):
            ans.append(arr[i][1])

        return ans


class Circle:
    def __init__(self, point, r):
        self.Point = point
        self.R = r

    def find_intersect(self, circle):
        x0, y0, r0 = self.Point.X, self.Point.Y, self.R
        x1, y1, r1 = circle.Point.X, circle.Point.Y, circle.R

        d = math.sqrt((x1-x0)**2 + (y1-y0)**2)

        # non intersecting
        if d > r0 + r1:
            return None
        # One circle within other
        if d < abs(r0-r1):
            return None
        # coincident circles
        if d == 0 and r0 == r1:
            return None
        else:
            a = (r0**2-r1**2+d**2)/(2*d)
            h = math.sqrt(r0**2-a**2)
            x2 = x0+a*(x1-x0)/d
            y2 = y0+a*(y1-y0)/d
            x3 = x2+h*(y1-y0)/d
            y3 = y2-h*(x1-x0)/d

            x4 = x2-h*(y1-y0)/d
            y4 = y2+h*(x1-x0)/d

            return (x3, y3), (x4, y4)


@app.route("/distance", methods=['POST'])
def calculate_distance():
    try:
        body = request.get_json()

        first_pos = _get_position(body['first_pos'])
        second_pos = _get_position(body['second_pos'])

        metric = 'euclidean'
        if('metric' in body):
            metric = body['metric']

        result = first_pos.distance(second_pos, metric)
        result = f"{result:.6f}"
        return jsonify(result=result), HTTPStatus.OK
    except MyException as e:
        return '', int(str(e))
    except:
        return '', HTTPStatus.BAD_REQUEST


@app.route("/nearest", methods=['POST'])
def calculate_nearest():
    try:
        body = request.get_json()

        ref = Point(body['ref_position'])

        k = 1
        if('k' in body):
            k = body['k']
        result = ref.find_nearest(k)
        return jsonify(robot_ids=result), HTTPStatus.OK
    except MyException as e:
        return '', int(str(e))


def _get_position(inp):
    if(type(inp) == str):
        if(robot_regex.fullmatch(inp)):
            robot_id = str(inp.split('#')[1])
            if(robot_id not in variables['robots']):
                return None
            return variables['robots'][robot_id]
        else:
            raise MyException('424')
    else:
        return Point(inp)


@app.route("/robot/<robot_id>/position", methods=['PUT'])
def put_variable(robot_id):
    try:
        body = request.get_json()

        robot_id = int(robot_id)

        if(robot_id < 1 or robot_id > 999999):
            raise MyException('400')
        if(('position' not in body)):
            raise MyException('400')

        variables['robots'][str(robot_id)] = Point(body['position'])
        return '', HTTPStatus.NO_CONTENT
    except MyException as e:
        return '', int(str(e))
    except:
        return '', HTTPStatus.BAD_REQUEST


@app.route("/robot/<robot_id>/position", methods=['GET'])
def get_robot(robot_id):
    try:
        value = __get_robot_position(robot_id)
        return jsonify(position=value), HTTPStatus.OK
    except MyException as e:
        return '', int(str(e))
    except:
        return '', HTTPStatus.BAD_REQUEST


def __get_robot_position(robot_id):
    if robot_id not in variables['robots']:
        raise MyException('404')
    else:
        return variables['robots'][str(robot_id)].to_object()


@app.route("/closestpair", methods=['GET'])
def get_closestpair():
    try:
        closest = None
        for k1, v1 in variables['robots'].items():
            for k2, v2 in variables['robots'].items():
                if(k1 == k2):
                    continue
                dist = v1.distance(v2)
                if(closest == None):
                    closest = dist
                elif(dist < closest):
                    closest = dist
        if(closest == None):
            raise MyException('424')
        else:
            return jsonify(distance=closest), HTTPStatus.OK
    except MyException as e:
        return '', int(str(e))
    except:
        return '', HTTPStatus.BAD_REQUEST


# TODO
@app.route("/alien/{object_dna}/report", methods=['POST'])
def report_alien(object_dna):
    try:
        body = request.get_json()

        robot_id = body['robot_id']
        distance = body['distance']

        new_circle = Circle(__get_robot_position(robot_id), distance)
        if(object_dna not in variables['aliens']):
            variables['aliens'][object_dna] = {
                'circle': new_circle,
                'intersect': None
            }
        else:
            if(variables['aliens'][object_dna]['intersect'] == None):
                points = variables['aliens'][object_dna]['circle'].find_intersect(
                    new_circle)
                if(points != None):
                    variables['aliens'][object_dna]['intersect'] = points
            else:
                pass
    except MyException as e:
        return '', int(str(e))
    except:
        return '', HTTPStatus.BAD_REQUEST
