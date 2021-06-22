import sys
import json
import base64
import hashlib
from io import StringIO
from random import randint
from multiprocessing import Process
from pathlib import Path
from urllib import request

# --------------------------------------------------------------------------- #

SOFTWARE_VERSION = "1.2"
DATA_URL = 'https://raw.githubusercontent.com/gsinclair/learninformatics/master/DATA.txt'
CODE_URL = 'https://raw.githubusercontent.com/gsinclair/learninformatics/master/learninformatics.py'
DATA_TXT_FILENAME = 'DATA.txt'
CODE_FILENAME = 'learninformatics.py'
DATA = None           # This is set in the course of usage.

# --------------------------------------------------------------------------- #

def error(message):
    print(message, file=sys.stderr)
    exit(1)

# --------------------------------------------------------------------------- #

def update(what='data'):
    if what == 'data':
        global DATA
        Path(DATA_TXT_FILENAME).unlink()
        request.urlretrieve(DATA_URL, DATA_TXT_FILENAME)
        print("DATA.txt updated from GitHub")
        DATA = None  # Force refresh
        load_data()
    elif what == 'code':
        Path(CODE_FILENAME).unlink()
        request.urlretrieve(CODE_URL, CODE_FILENAME)
        print("Code updated from guthub. Reload to see changes (if any)")
        print("Current code version (before update) is", SOFTWARE_VERSION)
    else:
        print("Argument to update() must be 'data' (default) or 'code'")
        print("No action taken")

def load_data():
    """Return DATA if it's valid. Or load DATA.txt if it exists. Or download it
       if it doesn't"""
    global DATA
    if DATA is not None:
        return DATA
    p = Path(DATA_TXT_FILENAME)
    if p.is_file():
        x = p.read_text()
        if len(x) < 100:
            raise ValueError("Invalid data in DATA.txt -- too short")
        x = x.encode('ascii')
        x = base64.decodebytes(x)
        x = x.decode('ascii')
        DATA = json.loads(x)
        return DATA
    else:
        update()
        return load_data()

# --------------------------------------------------------------------------- #

def info():
    def _groupby(seq, f):
        result = dict()
        for x in seq:
            k = f(x)
            if k in result:
                result[k].append(x)
            else:
                result[k] = [x]
        return result
    data = load_data()
    print("Program version:", SOFTWARE_VERSION)
    print("Data version:   ", data["meta"]["data_version"])
    print("Exercises available:")
    x = list(data["meta"]["mapping"].keys())
    x.sort
    for l in _groupby(x, lambda s: s[0]).values():
        print("  ", *l)



def _get_function(number):
    """Return ('ok', function) or ('notfound', None) or ('invalid', None)
       Invalid occurs when `number` is not three digits."""
    if 100 <= number < 1000:
        function_name = f'ex{number}'
        _locals = sys._getframe(2).f_locals
        if function_name in _locals:
            f = _locals[function_name]
            return ('ok', f)
        else:
            print(f"ERROR: Looking for function '{function_name}' but can't find it")
            return ('notfound', None)
    else:
        print(f'ERROR: Invalid exercise number: {number}')
        return ('invalid', None)


def run(function_id, data=None):
    """Runs the user-supplied or use-implied function with two arguments IN and OUT set to
       stdin and stdout respectively. This enables interactive running of user code.
       If function_id is a three-digit integer, then find the corresponding function in
       the user's environment (e.g. ex203).
       Otherwise function_id is taken to be an actual function.
       If _data_ is provided, this forms the input instead of stdin. It should,
       if necessary, be a multi-line string."""
    if type(function_id) == int:
        status, f = _get_function(function_id)
        if status != 'ok':
            return
    elif type(function_id) == type(info):
        f = function_id

    if data is None:
        f(sys.stdin, sys.stdout)
    else:
        data = StringIO(data)
        f(data, sys.stdout)


def _problem_data(number):
    data = load_data()
    try:
        problem_id = data["meta"]["mapping"][str(number)]
        return data[problem_id]
    except KeyError:
        return None


def test(number):
    """For the given problem number, runs the user-supplied function with
       the samples data and prints a helpful message (i.e. detailing
       the data) if it doesn't pass.
       A number of (say) 302 implies a function name ex302."""
    assert type(number) == int

    status, function = _get_function(number)
    if status != 'ok':
        return

    data = _problem_data(number)
    if data is None:
        e = sys.stderr
        print(f"Unable to access problem data for number '{number}'", file=e)
    else:
        print(f"Running sample data for problem: {data['name']}")
        testdata, newline = data['samples'], data['newline']
        testdata = input_output_pairs(testdata, newline)
        results = run_and_collect_results(function, testdata)
        for status, datain, dataout, expected in results:
            if status != 'AC':
                print_helpful_info(status, datain, dataout, expected)
        print_and_return_result_summary(results)
    print()
    

def judge(number):
    """For the given problem name, runs the user-supplied function with
       the prepared judging data and prints the result (AC, WA, ...) for
       each test case."""
    status, function = _get_function(number)
    if status != 'ok':
        return

    data = _problem_data(number)
    if data is None:
        e = sys.stderr
        print(f"Unable to access problem data for number '{number}'", file=e)
    else:
        print(f"Running judging data for problem: {data['name']}")
        judgedata, newline = data['judge'], data['newline']
        judgedata = list(input_output_pairs(judgedata, newline))
        if 'autojudge' in data and data['autojudge'] != '':
            function_name, n = data['autojudge']
            pairs = auto_generated_pairs(function_name, n)
            judgedata.extend(pairs)
        results = run_and_collect_results(function, judgedata)
        summary = print_and_return_result_summary(results)
        print()
        if all(x[0] == 'AC' for x in results):
            print("TOKEN:", token(number))
        else:
            print('Better luck next time')
    print()

# --------------------------------------------------------------------------- #

def run_and_collect_results(function, inoutpairs):
    """Runs the function on all available data in the generator inoutpairs.
       Returns a list of tuples: (status, instr, outstr, expected).
       The reported status is 'AC' or 'WA' or 'RTE'.
       In future, status may be 'TLE' or other values.
       The strings 'outstr' and 'expected' are stripped for ease of
       comparison."""
    result = []
    for datain, expected in inoutpairs:
        _in, _out = StringIO(datain), StringIO()
        try:
            # TODO implement Process
            function(_in, _out)
            dataout = _out.getvalue().strip()
            expected = expected.strip()
            if dataout == expected:
                x = ('AC', datain, dataout, expected)
            else:
                x = ('WA', datain, dataout, expected)
        except Exception as exc:
            x = ('RTE', datain, exc, expected)
        result.append(x)
        _in.close(); _out.close()
    return result

def input_output_pairs(data, newline):
    """The given data is a list of [in, out, in, out, ...].
       Each 'in' may be a string representing many lines, but compressed into
       a readable string using (say) full-stop as newline. The _newline_
       argument tells us what this special character is.
       The same applies to each 'out' string.
       Yields tuples (in, out), where both are strings and in probably contains
       actual newline characters."""
    for i in range(0, len(data), 2):
        a = '\n'.join(data[i+0].split(newline))
        b = '\n'.join(data[i+1].split(newline))
        yield (a,b)

def auto_generated_pairs(function_name, n):
    """The given function name is called n times from the AutoJudge class
       to generate input/output pairs."""
    f = getattr(AutoJudge, function_name)
    return [f(i) for i in range(1, n+1)]

def print_helpful_info(status, inputdata, useranswer, correctanswer):
    """This is to be called when the user is _testing_ their code,
       not _judging_ it."""
    if status == 'WA':
        print()
        print('--------------------------------------------------------')
        print('(WA) Incorrect answer given')
        print('Input data:')
        for x in inputdata.split('\n'):
            print('  ', x)
        print('Expected answer:')
        for x in correctanswer.split('\n'):
            print('  ', x)
        print('Your answer:')
        for x in useranswer.split('\n'):
            print('  ', x)
        print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
    elif status == 'RTE':
        print()
        print('--------------------------------------------------------')
        print('(RTE) Your code caused an error')
        print('Input data:')
        for x in inputdata.split('\n'):
            print('  ', x)
        print('Error:')
        for x in str(useranswer).split('\n'):
            print('  ', x)
        print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
    elif status == 'TLE':
        print()
        print('--------------------------------------------------------')
        print('(TLE) Time limit exceeded')
        print('Input data:')
        for x in inputdata.split('\n'):
            print('  ', x)
        print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

def print_and_return_result_summary(results):
    """Print the result (AC, WA, TLE, RTE) for each test case, and return
       a dictionary of the counts for each status."""
    prefix = { 'AC': '', 'WA': '    ', 'TLE': '        ', 'RTE': ' '*12 }
    summary = dict()
    n = 0
    print()
    for status, _, _, _ in results:
        n += 1
        print(f"Test {n:2d}: {prefix[status]}{status}")
        if status in summary:
            summary[status] += 1
        else:
            summary[status] = 1
    return summary

def token(number):
    """Return a six-digit hex token based on the problem number as evidence
       of success."""
    string = str(number ** 3)
    t = hashlib.sha224(string.encode('ascii')).hexdigest()[:6].upper()
    return f'{number}-{t}'

# --------------------------------------------------------------------------- #

class AutoJudge:
    """Implements functions to create random test data (and correct answers)
       so that large data sets can be tested without having to write them
       manually and clutter the data file."""

    @staticmethod
    def cutenumbers(n):
        out = StringIO()
        baselength = 10000 + randint(1000,2000) * n
        endlength  = randint(2000,3000) * n
        totallength = 1 + baselength + endlength
        print(totallength, file=out)
        print(randint(20,100), file=out)   # first one is nonzero
        for _ in range(baselength):
            if randint(1,20) == 1:
                print(0, file=out)
            else:
                print(randint(0,100000), file=out)
        for _ in range(endlength):
            print(0, file=out)
        return (out.getvalue(), f'{endlength}\n')

    @staticmethod
    def drought(n):
        out = StringIO()
        N = max(1000, n*200)
        C = 1000000
        avg = C // N
        data = [randint(avg//2, avg*3) for _ in range(N)]
        total, i = 0, 0
        while total < C:
            total += data[i]
            i += 1
        answer = i
        print(N, file=out)
        print(C, file=out)
        print(*data, sep='\n', file=out)
        return (out.getvalue(), f'{answer}\n')

    @staticmethod
    def ladybugs(n):
        out = StringIO()
        N = max(1000000, 100000 * n)
        a, b = 1000000000, 0
        print(N, file=out)
        for _ in range(N):
            x = randint(1,1000000000)
            print(x, file=out)
            a, b = min(a,x), max(b,x)
        return (out.getvalue(), f'{b-a+1}\n')

# --------------------------------------------------------------------------- #

