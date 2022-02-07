import{r as n,A as o,l as a}from"./app.a68c96d4.js";import"./vendor.f8864ac5.js";function c(s){return`${new Date(s).toISOString()}`}n("LogsPage",class extends o{constructor(t){super(t)}enter(){let t=this.html,l=[];for(let e=0;e<a.num_items();e++)l.push(a.item(e));let i=t`
        <div class="container">
            <h2 class="mb-16 wball">${T("Displaying the technical logs")}</h2>

            <ul>
                ${l.map(({timestamp:e,desc:r},m)=>t`<li class="bb-1 wball">${c(e)}-${r}</li>`)}
            </ul>

        </div>`;this.render(i)}});
//# sourceMappingURL=LogsPage.114e300d.js.map
