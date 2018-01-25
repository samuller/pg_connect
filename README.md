# pg_connect

## Development

Setup a virtualenv (optional, but recommended):

    virtualenv -p python3 .env

    . .env/bin/activate

Then install required modules:

    pip install -r requirements.txt

Then you should be able to run:

    python pg_inspect.py --help

If you have a database set up then you can test connecting with it by using:

    python pg_inspect.py -d database -U user

