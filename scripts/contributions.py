#!/usr/bin/env python3
"""Rend le calendrier de contributions de l'année dans la charte du README.

Source des données, dans l'ordre :
  1. l'API GraphQL de GitHub si GITHUB_TOKEN est défini (dépôts privés inclus
     si l'option « Include private contributions » est activée sur le profil) ;
  2. sinon un fichier JSON {"YYYY-MM-DD": n, ...} passé en argument.

Usage : contributions.py [--user LOGIN] [--from-json fichier] [--out assets/contributions.svg]
"""
import argparse, datetime as dt, json, os, sys, urllib.request

# Charte (identique à celle des autres visuels)
BG="#161B22"; BORDER="#2A313C"; TXT="#F0F3F6"; SUB="#B6BEC9"; MUT="#8B949E"; ACC="#4CC2FF"
LEVELS=["#1C2330","#12385A","#0F5C96","#1E93DA","#4CC2FF"]
SANS="'Segoe UI Variable','Segoe UI',system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif"
MONTHS=["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."]
DAYS={1:"lun.",3:"mer.",5:"ven."}

def fetch_graphql(user, token):
    to=dt.datetime.now(dt.timezone.utc); frm=to-dt.timedelta(days=365)
    q='''query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
          contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'''
    body=json.dumps({"query":q,"variables":{"u":user,"f":frm.isoformat(),"t":to.isoformat()}}).encode()
    req=urllib.request.Request("https://api.github.com/graphql",data=body,
        headers={"Authorization":f"bearer {token}","Content-Type":"application/json","User-Agent":"contributions-svg"})
    with urllib.request.urlopen(req,timeout=30) as r: data=json.load(r)
    if "errors" in data: sys.exit(f"GraphQL : {data['errors']}")
    cal=data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return {d["date"]:d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]}

def level(n, mx):
    if n<=0: return 0
    if mx<=4: return min(n,4)
    return 1+min(3,int(3*(n-1)/max(1,mx-1)+0.999))

def render(counts, out):
    today=dt.date.today(); start=today-dt.timedelta(days=364)
    start-=dt.timedelta(days=(start.weekday()+1)%7)          # aligne sur un dimanche, comme GitHub
    days=[start+dt.timedelta(days=i) for i in range((today-start).days+1)]
    weeks=(len(days)+6)//7
    cell,gap=16,4; left,top=64,44; W=1200; H=top+7*(cell+gap)+58
    mx=max([counts.get(d.isoformat(),0) for d in days]+[1]); total=sum(counts.get(d.isoformat(),0) for d in days)
    grid_w=weeks*(cell+gap)-gap; left=(W-grid_w)//2+16
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{total} contributions sur un an">',
       f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
       (f'<text x="{left}" y="28" font-family="{SANS}" font-size="14" font-weight="600" fill="{TXT}">{total} contributions sur les douze derniers mois</text>' if counts else
        f'<text x="{left}" y="28" font-family="{SANS}" font-size="14" font-weight="600" fill="{TXT}">Calendrier des contributions</text>'),
       f'<text x="{W-40}" y="28" text-anchor="end" font-family="{SANS}" font-size="11.5" fill="{MUT}">{"mis à jour le "+today.strftime("%d/%m/%Y") if counts else "mise à jour automatique chaque nuit"}</text>']
    for wd,lab in DAYS.items():
        s.append(f'<text x="{left-10}" y="{top+wd*(cell+gap)+cell-4}" text-anchor="end" font-family="{SANS}" font-size="11" fill="{MUT}">{lab}</text>')
    seen=set()
    for i,d in enumerate(days):
        w,r=divmod((d-start).days,7); x=left+w*(cell+gap); y=top+r*(cell+gap)
        if d.day<=7 and (d.year,d.month) not in seen and w<weeks-1:
            seen.add((d.year,d.month)); s.append(f'<text x="{x}" y="{top-10}" font-family="{SANS}" font-size="11" fill="{MUT}">{MONTHS[d.month-1]}</text>')
        n=counts.get(d.isoformat(),0); c=LEVELS[level(n,mx)]
        s.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{c}"><title>{d.strftime("%d/%m/%Y")} : {n} contribution{"s" if n>1 else ""}</title>'
                 f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{min(.95,w/weeks*.85):.3f};1" dur="1.6s" fill="freeze"/></rect>')
    ly=H-24; lx=W-40-5*(cell+gap)-52
    s.append(f'<text x="{lx-8}" y="{ly+12}" text-anchor="end" font-family="{SANS}" font-size="11" fill="{MUT}">moins</text>')
    for i,c in enumerate(LEVELS): s.append(f'<rect x="{lx+i*(cell+gap)}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')
    s.append(f'<text x="{lx+5*(cell+gap)+4}" y="{ly+12}" font-family="{SANS}" font-size="11" fill="{MUT}">plus</text>')
    s.append('</svg>')
    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
    open(out,"w",encoding="utf-8").write("\n".join(s)); print(f"{out} : {total} contributions, max {mx}/jour")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--user",default=os.environ.get("GH_USER","Walpole13"))
    ap.add_argument("--from-json"); ap.add_argument("--out",default="assets/contributions.svg"); a=ap.parse_args()
    tok=os.environ.get("GITHUB_TOKEN")
    counts=fetch_graphql(a.user,tok) if tok and not a.from_json else json.load(open(a.from_json))
    render(counts,a.out)
