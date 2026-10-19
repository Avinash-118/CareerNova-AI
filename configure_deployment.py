"""Generate Vercel's same-origin API proxy once the backend URL is known."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def vercel_config(backend):
    value=backend.rstrip('/')
    parsed=urlparse(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('Use a backend HTTPS origin, without a path, credentials or query string.')
    return {'$schema':'https://openapi.vercel.sh/vercel.json','framework':'vite',
            'buildCommand':'npm run build','outputDirectory':'dist',
            'rewrites':[{'source':'/api/:path*','destination':value+'/api/:path*'},
                        {'source':'/((?!api/).*)','destination':'/index.html'}],
            'headers':[{'source':'/(.*)','headers':[
                {'key':'X-Content-Type-Options','value':'nosniff'},
                {'key':'Referrer-Policy','value':'no-referrer'},
                {'key':'Permissions-Policy','value':'camera=(), geolocation=(), microphone=(self)'}]}]}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--backend',required=True);args=parser.parse_args()
    path=Path(__file__).resolve().parent/'frontend'/'vercel.json'
    path.write_text(json.dumps(vercel_config(args.backend),indent=2)+'\n',encoding='utf-8')
    print('Vercel routing configured. Set the Vercel project Root Directory to frontend and leave VITE_API_URL empty.')
