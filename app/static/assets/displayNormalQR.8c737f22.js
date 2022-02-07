import{r as a,A as l}from"./app.a68c96d4.js";import"./vendor.f8864ac5.js";a("DisplayNormalQR",class extends l{constructor(r){super(r)}enter(r){let e=this.html,s=!1;(r.startsWith("https://")||r.startsWith("http://"))&&(s=!0);let t=e`
        <div class="container" style="margin-top:50px;">
            <h2 class="mb-16 center">Received QR</h2>
            <p class="w3-large" style="word-break: break-all;">${r}</p>
        
            <div class="w3-bar ptb-16 w3-center" style="max-width:70%;margin:50px auto;">

                <a href="javascript:void(0)" @click=${()=>window.history.back()} class="btn left color-secondary hover-color-secondary
                    w3-large w3-round-xlarge">Back</a>
    
                ${s?e`<a href="${r}" class="btn right color-secondary hover-color-secondary
                    w3-large w3-round-xlarge">Go to site</a>`:e``}
                
            </div>
        </div>
        `;this.render(t)}});
//# sourceMappingURL=displayNormalQR.8c737f22.js.map
