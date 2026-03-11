"""lookup — check CRM for existing PWD record by case number."""
import click, requests

API_KEY  = '191c7a64c19cab5cb7a18954f165f3a2'
CRM_BASE = 'https://crm.permtrak.com/EspoCRM/api/v1'

@click.command('lookup')
@click.argument('case_number')
def lookup(case_number):
    """Look up a PWD record in CRM by case number."""
    r = requests.get(f'{CRM_BASE}/PWD',
        headers={'X-Api-Key': API_KEY, 'User-Agent': 'pwdx-ctl/0.1'},
        params={'where[0][type]':'equals','where[0][attribute]':'casenumber','where[0][value]':case_number,
                'select':'id,name,casenumber,addendumjobduties,addendumeduc,addendumsoc,createdAt','maxSize':3},
        timeout=15)
    hits = r.json().get('list', [])
    if not hits:
        click.echo(click.style(f'[NOT FOUND] No PWD record for {case_number}', fg='yellow'))
        return
    for h in hits:
        click.echo(click.style(f"[FOUND] {h.get('name')} — {h.get('id')}", fg='green'))
        click.echo(f"  URL: https://crm.permtrak.com/EspoCRM/#PWD/view/{h['id']}")
        for af in ('addendumjobduties','addendumeduc','addendumsoc'):
            if h.get(af):
                click.echo(click.style(f'  {af}:', fg='yellow') + f" {str(h[af])[:120]}")
