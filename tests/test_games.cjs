const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto').webcrypto;
const nodes=new Map();function node(){return {value:'',textContent:'',hidden:false,disabled:false,children:[],append(...x){this.children.push(...x)},replaceChildren(){this.children=[]}};}
const document={getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},createElement:node};
const core=fs.readFileSync('core.py','utf8');const html=core.slice(core.indexOf("HTML = r'''"));const rules=html.slice(html.indexOf('<script>')+8,html.indexOf('</script>'));
const context={document,crypto};vm.createContext(context);vm.runInContext(rules,context);
vm.runInContext(`
 const h=(ranks,suits)=>ranks.map((rank,i)=>({rank,suit:suits[i]}));
 const samples=[
 h([14,13,12,11,9],['♠','♥','♦','♣','♠']),
 h([14,14,12,11,9],['♠','♥','♦','♣','♠']),
 h([14,14,12,12,9],['♠','♥','♦','♣','♠']),
 h([14,14,14,11,9],['♠','♥','♦','♣','♠']),
 h([14,5,4,3,2],['♠','♥','♦','♣','♠']),
 h([14,13,12,11,9],['♠','♠','♠','♠','♠']),
 h([14,14,14,11,11],['♠','♥','♦','♣','♠']),
 h([14,14,14,14,9],['♠','♥','♦','♣','♠']),
 h([14,13,12,11,10],['♠','♠','♠','♠','♠'])];
 globalThis.categories=samples.map(x=>pokerRank(x)[0]);
 globalThis.wheel=pokerRank(samples[4]);
 globalThis.tie=compareHands(samples[8],samples[8]);
 globalThis.cardCount=tarotDeck().length;
`,context);
assert.deepEqual(Array.from(context.categories),[0,1,2,3,4,5,6,7,8]);assert.equal(context.wheel[1],5);assert.equal(context.tie,0);assert.equal(context.cardCount,78);
nodes.get('stud-new').onclick();assert.match(nodes.get('stud-dezzy').textContent,/Hidden/);
for(let i=0;i<4;i++)nodes.get('stud-next').onclick();assert.doesNotMatch(nodes.get('stud-dezzy').textContent,/Hidden/);assert.equal(nodes.get('stud-next').disabled,true);assert.match(nodes.get('stud-status').textContent,/wins|win|tie/);
nodes.get('stud-tab').onclick();assert.equal(nodes.get('tarot-panel').hidden,true);assert.equal(nodes.get('stud-panel').hidden,false);
nodes.get('tarot-tab').onclick();nodes.get('tarot-deal').onclick();assert.equal(nodes.get('tarot-cards').children.length,3);assert.equal(nodes.get('stud-panel').hidden,true);
console.log('Game checks passed: all poker categories, ace-low straight, ties, complete stud hand, tarot draw, tab switching.');
