import sys
import json
import yaml
import base64
import hashlib
import shutil
from io import StringIO
from random import randint
from multiprocessing import Process
from pathlib import Path
import urllib.request

# Coming improvements:
#  * handle large tests in separate file
#  * use Process to enable timeout enforcement
#  * improve printing of error and info messages (too many blank lines)

# --------------------------------------------------------------------------- #

SOFTWARE_VERSION = "2.0"
VERS_URL = 'https://raw.githubusercontent.com/gsinclair/learninformatics/master/VERSION.json'
DATA_URL = 'https://raw.githubusercontent.com/gsinclair/learninformatics/master/DATA.txt'
CODE_URL = 'https://raw.githubusercontent.com/gsinclair/learninformatics/master/learninformatics.py'
BOOK_URL = 'bit.ly/hsifcb'
DATA_FILENAME = 'DATA.txt'                # Todo 2 filenames
CODE_FILENAME = 'learninformatics.py'

DEBUG_LEARNINFORMATICS = False

HELP = """
Helpful commands:
 * l.help()              - you're reading it
 * l.info()              - print versions and exercise numbers
 * l.exercises()         - print exercise numbers and names

Completing exercises:
 * l.run(107)            - run function 'ex107' with keyboard and screen
 * l.test(107)           - run function 'ex107' with test data
                           (probably just the sample(s) in the problem statement)
 * l.judge(107)          - run function 'ex107' with judging data and award
                           a token if all inputs give the correct output
Result codes:
 * AC                    - all correct (the correct output was given)
 * WA                    - wrong answer (incorrect output was given)
 * RTE                   - run-time exception (the code crashed)
 * TLE                   - time limit exceeded (generally 2 seconds)

Advanced:
 * l.run(func)           - run any function you like (it must have IN and OUT)
 * l.run(107, '56\\n42\\n')      - run 'ex107' with the given data
 * l.run(func, '56\\n42\\n')     - run any function with the given data

     (Providing data to l.run(...) could save time when you want to test
      something specific repeatedly.)
"""

# --------------------------------------------------------------------------- #

def info():
    """Gives info about code and data versions and which exercise numbers are
       supported."""
    Interface.info()

def exercises():
    """Gives detail about exercise numbers and their corresponding problem names."""
    Interface.exercises()

def help():
    """Provides overview of all available commands."""
    print(HELP)

def update():
    """Update data and code if needed by checking availability of newer versions."""
    Interface.update()

def force_update():
    """Force update of data and code; to be used if something is wrong."""
    Interface.force_update()

def run(*args):
    """Run a function with optional data given.

       run(107)            -- runs function 'ex107' with keyboard and screen
       run(107, '56\n')    -- runs function 'ex107' with given input and screen
       run(mycode)         -- runs function 'mycode' with keyboard and screen
       run(mycode, '56\n') -- runs function 'mycode' with given input and screen

       Note that 'given input' would often be several lines."""
    Interface.run(*args)

def test(number):
    """Run an exercise function with test data (the samples described in the problem
       and possibly some more) and give informative report if there is failure.

       l.test(107)         -- tests exercise 107 (function 'ex107')"""
    Interface.test(number)

def judge(number):
    """Run an exercise function with judging data which is kept secret in the event
       of a failure. Basic information provided (AC, WA, etc.).

       l.judge(107)        -- judges exercise 107 (function 'ex107')"""
    Interface.judge(number)

# --------------------------------------------------------------------------- #

class LIData:
    """Handles the initialisation, interface and update for the learninformatics data
    sets"""
    def __init__(s):
        s.data = s._data_from_file()
        if s.data is None:
            Impl.info("You have no data file, so I'll download it")
            s._force_update()

    def is_ok(s):
        """Basic sanity check on our data"""
        return type(s.data) == type(dict()) and len(s.data) > 0

    def version(s):
        return s.data['meta']['data_version']

    def exercise_numbers(s):
        return list(s.data['meta']['mapping'].keys())

    def problem_name(s, number):
        codename =  s.data['meta']['mapping'][number]
        return s.data[codename]['name']

    def problem_data(s, number):
        try:
            codename =  s.data['meta']['mapping'][str(number)]
            return s.data[codename]
        except KeyError:
            return None

    def _data_from_file(s):
        """Returns the data dictionary, or None if there is no file"""
        p = Path(DATA_FILENAME)
        if p.is_file():
            x = p.read_text()
            if len(x) < 100:
                Impl.error('Invalid data in DATA.txt (too short)',
                           'Please run l.update()')
                return
            x = x.encode('ascii')
            x = base64.decodebytes(x)
            x = x.decode('ascii')
            return yaml.load(x)
        else:
            return None

    def _force_update(s):
        """Attempt an update of the data file."""
        if s._update_from_github():
            s.data = s._data_from_file()

    def _update_from_github(s):
        """Downloads the data file from Github; doesn't activate it.
           Returns True on success, or False on failure."""
        tmpfile = DATA_FILENAME + '.tmp'
        try:
            localname, _ = urllib.request.urlretrieve(DATA_URL)
            if Path(DATA_FILENAME).is_file():
                Path(DATA_FILENAME).unlink()
            shutil.copy(localname, DATA_FILENAME)
            Impl.info("DATA.txt updated from GitHub")
            return True
        except urllib.request.ContentTooShortError:
            Impl.error("Updating the data was only partially successful; try again")
            return False
        except urllib.request.URLError:
            Impl.error("Unable to update data; check Internet connection")
            return False


# --------------------------------------------------------------------------- #

class Interface:
    data = None        # This will be set at the bottom of the file, to get around
                       # forward-declaration problems.

    @staticmethod
    def ensure_data():
        if Interface.data.is_ok():
            return Interface.data
        else:
            Impl.error('No data to work with',
                       'Try l.update() if you have Internet connection')

    @staticmethod
    def update():
        data = Interface.ensure_data()
        version_info = Impl.version_info()
        if version_info is None:
            Impl.error("Tried but failed to find latest version information")
            return

        if Impl.lower_version(data.version(), version_info['data']):
            Impl.info('More recent data available; updating')
            data._force_update()
        else:
            print(f'Your data is at the latest version ({data.version()})')

        if Impl.lower_version(SOFTWARE_VERSION, version_info['software']):
            Impl.info('More recent software available; updating')
            Impl.update_software()
        else:
            print(f'Your software is at the latest version ({SOFTWARE_VERSION})')

        print(f'The best available book version is {version_info["book"]}.')
        print(f'  [Update from {BOOK_URL} if necessary.]')


    @staticmethod
    def force_update():
        data = Interface.ensure_data()
        data._force_update()
        Impl.update_software()

    # TODO: include book version  --- um, how?
    @staticmethod
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
        data = Interface.ensure_data()
        print()
        print("Program version:", SOFTWARE_VERSION)
        print("Data version:   ", data.version())
        print("Exercises available:")
        x = data.exercise_numbers()
        x.sort
        for l in _groupby(x, lambda s: s[0]).values():
            print("  ", *l)
        print("Run l.exercises() for more detailed info on exercises")
        print()

    @staticmethod
    def exercises():
        print()
        data = Interface.ensure_data()
        for n in data.exercise_numbers():
            print(f' * {n}  {data.problem_name(n)}')
        print()

    @staticmethod
    def run(function_id, data=None):
        """Runs the user-supplied or user-implied function with two arguments IN and OUT
           set to stdin and stdout respectively. This enables interactive running of user
           code.  If function_id is a three-digit integer, then find the corresponding
           function in the user's environment (e.g. ex203).
           Otherwise function_id is taken to be an actual function.
           If _data_ is provided, this forms the input instead of stdin. It should,
           if necessary, be a multi-line string."""
        if type(function_id) == int:
            status, f = Impl.get_function(function_id)
            if status != 'ok':
                return
        elif type(function_id) == type(info):
            f = function_id

        if data is None:
            f(sys.stdin, sys.stdout)
        else:
            data = StringIO(data)
            f(data, sys.stdout)

    @staticmethod
    def test(number):
        """For the given problem number, runs the user-supplied function with
           the samples data and prints a helpful message (i.e. detailing
           the data) if it doesn't pass.
           A number of (say) 302 implies a function name ex302."""
        assert type(number) == int
        data = Interface.ensure_data()

        status, function = Impl.get_function(number)
        if status != 'ok':
            return

        pd = data.problem_data(number)
        if pd is None:
            Impl.error(f"Unable to access problem data for number '{number}'")
        else:
            print()
            print(f"Running sample data for problem: {pd['name']}")
            testdata, newline = pd['samples'], pd['newline']
            testdata = Judge.input_output_pairs(testdata, newline)
            results = Judge.run_and_collect_results(function, testdata)
            for status, datain, dataout, expected in results:
                if status != 'AC':
                    Judge.print_helpful_info(status, datain, dataout, expected)
            Judge.print_and_return_result_summary(results)
        print()

    @staticmethod
    def judge(number):
        """For the given problem name, runs the user-supplied function with
           the prepared judging data and prints the result (AC, WA, ...) for
           each test case."""
        assert type(number) == int
        data = Interface.ensure_data()

        status, function = Impl.get_function(number)
        if status != 'ok':
            return

        pd = data.problem_data(number)
        if pd is None:
            Impl.error(f"Unable to access problem data for number '{number}'")
        else:
            print()
            print(f"Running judging data for problem: {pd['name']}")
            judgedata, newline = pd['judge'], pd['newline']
            judgedata = list(Judge.input_output_pairs(judgedata, newline))
            if 'autojudge' in pd and pd['autojudge'] != '':
                function_name, n = pd['autojudge']
                pairs = Judge.auto_generated_pairs(function_name, n)
                judgedata.extend(pairs)
            results = Judge.run_and_collect_results(function, judgedata)
            summary = Judge.print_and_return_result_summary(results)
            print()
            if all(x[0] == 'AC' for x in results):
                print("TOKEN:", Impl.token(number, pd['name']))
            else:
                print('Better luck next time')
        print()

# --------------------------------------------------------------------------- #

class Impl:
    @staticmethod
    def info(*lines):
        """A useful way of printing an info message of one or more lines in a
           clear and consistent way."""
        print()
        print("INFO:", lines[0])
        if len(lines) > 1:
            for i in range(1, len(lines)):
                print("     ", lines[i])
        print()

    @staticmethod
    def error(*lines):
        """A useful way of printing an error message of one or more lines in a
           clear and consistent way."""
        print()
        print("ERROR:", lines[0])
        if len(lines) > 1:
            for i in range(1, len(lines)):
                print("      ", lines[i])
        print()

    @staticmethod
    def version_info():
        """Returns dictionary, or None if unable to download."""
        try:
            x = urllib.request.urlopen(VERS_URL).read()
            return json.loads(x)
        except urllib.request.URLError:
            return None

    @staticmethod
    def lower_version(a, b):
        """'1.3', '1.4' --> True"""
        version_a = [int(x) for x in a.split('.')]
        version_b = [int(x) for x in b.split('.')]
        return version_a < version_b

    @staticmethod
    def get_function(number):
        """Return ('ok', function) or ('notfound', None) or ('invalid', None)
           Invalid occurs when `number` is not three digits."""
        if 100 <= number < 1000:
            function_name = f'ex{number}'
            _locals = sys._getframe(3).f_locals
            if function_name in _locals:
                f = _locals[function_name]
                return ('ok', f)
            else:
                Impl.error(f"Looking for function '{function_name}' but can't find it")
                return ('notfound', None)
        else:
            Impl.error(f'Invalid exercise number: {number}')
            return ('invalid', None)

    @staticmethod
    def token(number, codename):
        """Return a six-digit hex token based on the problem codename, appended to the
           problem number, as evidence of success."""
        t = hashlib.sha224(codename.encode('ascii')).hexdigest()[:6].upper()
        return f'{number}-{t}'

# --------------------------------------------------------------------------- #

class Judge:

    @staticmethod
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
                if DEBUG_LEARNINFORMATICS: print(exc)
                x = ('RTE', datain, exc, expected)
            result.append(x)
            _in.close(); _out.close()
        return result

    @staticmethod
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

    @staticmethod
    def auto_generated_pairs(function_name, n):
        """The given function name is called n times from the AutoJudge class
           to generate input/output pairs."""
        f = getattr(AutoJudge, function_name)
        return [f(i) for i in range(1, n+1)]

    @staticmethod
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

    @staticmethod
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

# --------------------------------------------------------------------------- #

# TODO Get rid of this by implementing fixed large test data.
# Or maybe not. At least consider it.
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

Interface.data = LIData()

print("""
=====================================================
*    Welcome to the learninformatics environment    *
*    Run l.help() to see available commands         *
=====================================================
""")
