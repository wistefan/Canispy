import{r as o,A as c,l as d}from"./app.a68c96d4.js";import{C as h,v as g}from"./verifications.3e2b6b33.js";import{o as m,w as v,e as f}from"./warning.e1565ac2.js";import"./vendor.f8864ac5.js";import"./_commonjsHelpers.4e997714.js";o("DisplayMyHcert",class extends c{constructor(i){super(i)}async enter(i){let t=this.html;if(i=window.localStorage.getItem("MYEUDCC"),i==null){this.render(t`
            <div id="hcertFailed" class="w3-panel bkg-fail">
                <h2>${T("There is no certificate.")}</h2>
            </div>
            `);return}let a,r=!1,s="";try{a=await h.decodeHC1QR(i,!0),r=a[3]}catch(l){d.error("Error verifying credential",l),this.render(this.renderGeneralError(l));return}let e={result:"OK",message:T("The certificate is valid.")};r===!1?(e.result="ERROR",e.message=T("Signature validation failed. The certificate is not valid.")):r==="PRE"&&(e.result="WARNING",e.message=T("$warningmsg")),console.log(e),(r===!0||r==="PRE")&&(console.log("Additional verifications"),r=g(a),console.log(r),r!=!0&&(e.result="ERROR",e.message=T(r))),console.log(e);try{s=this.renderDetail(a,e)}catch(l){d.error("Error rendering credential",l),this.render(this.renderGeneralError(l));return}let n=t`
        ${s}
        <div class="sect-white">
            <button class="btn-primary" @click=${()=>this.gotoPage("DisplayQR")}>
            ${T("Display QR")}</button>
        </div>
        `;this.render(n)}renderGeneralError(i){return this.html`
            <div id="hcertFailed" class="w3-panel bkg-fail">
                <h3>Failed!</h3>
                <p>The credential has an invalid format.</p>
            </div>
            `}renderDetail(i,t){let a=this.html,r=i[1],s="Validated",e=m,n="bkg-success";return t.result==="WARNING"?(s="Warning",e=v,n="bkg-warning"):t.result==="ERROR"&&(s="Not Validated",e=f,n="bkg-error"),a`
            <div class="container">

                <div id="hcertWarning" class=${`w3-panel ${n}`}>
                    <img src=${e}  alt="" />
                    <h3>${T(s)}</h3>
                    <p>${t.message}</p>
                </div>

                <div class="section">
                    <div class="subsection">
                        <div class="etiqueta">${T("Surname and forename")}</div>
                        <div class="valor h4">${r.fullName}</div>
                    </div>
                    <div class="subsection">
                        <div class="etiqueta">${T("Date of birth")}</div>
                        <div class="valor h4">${r.dateOfBirth}</div>
                    </div>
                </div>
           
            </div>
        `}});
//# sourceMappingURL=DisplayMyHcert.c095bfb2.js.map
