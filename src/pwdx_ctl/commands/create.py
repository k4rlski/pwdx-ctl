"""create — push extracted fields to CRM PWD entity."""
import click, json, requests

API_KEY  = '191c7a64c19cab5cb7a18954f165f3a2'
CRM_BASE = 'https://crm.permtrak.com/EspoCRM/api/v1'
HDRS     = {'X-Api-Key': API_KEY, 'Content-Type': 'application/json', 'User-Agent': 'pwdx-ctl/0.1'}

FIELD_MAP = {
    'case_number':'casenumber','received_date':'datereceived','determination_date':'datedetermination',
    'contact_last_name':'employerpoclastname','contact_first_name':'employerpocfirstname',
    'contact_job_title':'employerpocjobtitle','contact_city':'employerpoccity',
    'contact_state':'employerpocstate','contact_zip':'employerpocpostalcode',
    'contact_phone':'employerpocphone','contact_email':'employerpocemail',
    'employer_name':'employerlegalbusinessname','employer_address1':'employeraddress1',
    'employer_city':'employercity','employer_state':'employerstate',
    'employer_zip':'employerpostalcode','employer_phone':'employerphone','employer_fein':'employerfein',
    'job_title':'jobtitle','job_duties':'jobdescription',
    'addendum_job_duties':'addendumjobduties','addendum_educ':'addendumeduc','addendum_soc':'addendumsoc',
    'soc_code':'occupationtitlecode','soc_title':'occupationtitledescription',
    'worksite_address1':'worksiteaddress1','worksite_city':'worksitecity',
    'worksite_state':'worksitestate','worksite_zip':'worksitepostalcode','worksite_county':'worksitecounty',
    'pwd_wage_rate':'pwdwagerate','pwd_unit_of_pay':'pwdunitofpay',
    'pwd_oews_wage_level':'pwdwagelevel','pwd_wage_source':'pwdwagesource',
    'pw_receipt_date':'datepwdreceived','pwd_wage_expiration_date':'datepwdwageexpiration',
    'bls_area':'blsarea','attorney_last_name':'agentattorneylastname',
    'attorney_first_name':'agentattorneyfirstname','attorney_email':'agentattorneyemailaddress',
    'law_firm':'lawfirmnamebusinessname',
}

def _create_from_fields(fields: dict):
    espo = {}
    for k, v in fields.items():
        ek = FIELD_MAP.get(k)
        if ek and v:
            espo[ek] = v
    espo.setdefault('name', fields.get('employer_name') or fields.get('case_number') or 'PWD Import')
    r = requests.post(f'{CRM_BASE}/PWD', json=espo, headers=HDRS, timeout=20)
    r.raise_for_status()
    rec = r.json()
    rid = rec.get('id', '')
    url = f'https://crm.permtrak.com/EspoCRM/#PWD/view/{rid}'
    click.echo(click.style(f'\n  ✓ Created PWD record: {espo["name"]}', fg='green'))
    click.echo(f'  URL: {url}')
    return rid, url

@click.command('create')
@click.option('--fields-file', default='/tmp/pwd_text_extracted.txt', help='Extracted fields file')
@click.option('--dry-run', is_flag=True)
def create(fields_file, dry_run):
    """Create CRM PWD record from last extraction."""
    import os
    if not os.path.exists(fields_file):
        click.echo(click.style(f'[ERROR] {fields_file} not found. Run extract first.', fg='red'))
        raise SystemExit(1)
    fields = {}
    with open(fields_file) as f:
        for line in f:
            if ': ' in line:
                k, v = line.split(': ', 1)
                k = k.strip()
                if k and len(k) < 60:
                    fields[k] = v.strip()
    click.echo(f'  {len(fields)} fields loaded from {fields_file}')
    if dry_run:
        click.echo(click.style('  [DRY RUN] Would create PWD record. Pass without --dry-run to write.', fg='yellow'))
        return
    _create_from_fields(fields)
