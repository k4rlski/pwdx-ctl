"""extract — PDF → parsed fields."""
import click, subprocess, os, sys, json

EXTRACTOR = '/home/openclaw/dev/pwdx-upload/scripts/extract_pwd_text_v2.py'
OUT_FILE   = '/tmp/pwd_text_extracted.txt'

@click.command('extract')
@click.argument('pdf_path')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.option('--create', is_flag=True, help='Create CRM record after extraction')
def extract(pdf_path, as_json, create):
    """Extract fields from an ETA-9141 PDF."""
    if not os.path.exists(pdf_path):
        click.echo(click.style(f'[ERROR] File not found: {pdf_path}', fg='red'))
        raise SystemExit(1)

    click.echo(click.style(f'pwdx-ctl extract: {os.path.basename(pdf_path)}', fg='cyan', bold=True))
    subprocess.run(['python3', EXTRACTOR, pdf_path], capture_output=True)

    fields = {}
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            for line in f:
                if ': ' in line:
                    k, v = line.split(': ', 1)
                    k = k.strip()
                    if k and len(k) < 60:
                        fields[k] = v.strip()

    if not fields:
        click.echo(click.style('[ERROR] No fields extracted.', fg='red'))
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(fields, indent=2))
        return

    # Display key fields
    KEY_FIELDS = ['case_number','employer_name','job_title','soc_code','pwd_wage_rate',
                  'pwd_unit_of_pay','pwd_oews_wage_level','worksite_state','worksite_zip',
                  'determination_date','pwd_wage_expiration_date',
                  'addendum_job_duties','addendum_educ','addendum_soc']
    click.echo('')
    for k in KEY_FIELDS:
        if k in fields and fields[k]:
            color = 'yellow' if k.startswith('addendum') else 'white'
            label = click.style(k + ':', fg='cyan')
            val = fields[k][:200] + ('...' if len(fields[k]) > 200 else '')
            click.echo(f'  {label} {val}')

    other = {k: v for k, v in fields.items() if k not in KEY_FIELDS and v}
    if other:
        click.echo(click.style(f'\n  + {len(other)} additional fields', fg='bright_black'))

    click.echo(click.style(f'\n  Total: {len(fields)} fields extracted', fg='green'))

    if create:
        from .create import _create_from_fields
        _create_from_fields(fields)
