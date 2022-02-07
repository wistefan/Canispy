import{r as n,A as d,l as o}from"./app.a68c96d4.js";import{C as c,v as m}from"./verifications.3e2b6b33.js";import{o as g,w as h,e as f}from"./warning.e1565ac2.js";import"./vendor.f8864ac5.js";import"./_commonjsHelpers.4e997714.js";n("DisplayHcert",class extends d{constructor(s){super(s)}async enter(s){let t,r=!1,i="";try{t=await c.decodeHC1QR(s,!0),r=t[3]}catch(a){o.error("Error verifying credential",a),this.render(this.renderGeneralError(a));return}let e={result:"OK",message:T("The certificate is valid.")};r===!1?(e.result="ERROR",e.message=T("Signature validation failed. The certificate is not valid.")):r==="PRE"&&(e.result="WARNING",e.message=T("$warningmsg")),console.log(e),(r===!0||r==="PRE")&&(console.log("Additional verifications"),r=m(t),console.log(r),r!=!0&&(e.result="ERROR",e.message=T(r))),console.log(e);try{i=this.renderDetail(t,e)}catch(a){o.error("Error rendering credential",a),this.render(this.renderGeneralError(a));return}let l=this.html`
        <div class="text-center">

            ${i}

            <button class="btn-primary" @click=${()=>this.gotoPage("ScanQrPage")}>
            ${T("Verify another")}</button>

        </div>
        `;this.render(l)}renderGeneralError(s){return this.html`
            <div id="hcertFailed" class="w3-panel bg-fail">
                <h3>Failed!</h3>
                <p>The credential has an invalid format.</p>
            </div>
            `}renderDetail(s,t){let r=s[1],i="Validated",e=g,l="bg-success";return t.result==="WARNING"?(i="Warning",e=h,l="bg-warning"):t.result==="ERROR"&&(i="Not Validated",e=f,l="bg-error"),this.html`

        <div class=${`py-3 mb-3 shadow-lg ${l}`}>
            <div class="flex justify-center">
                <img class="mr-2" src=${e}  alt="" />
                <h3 class="my-auto text-xl font-bold ml-2">${T(i)}</h3>                
            </div>
            <p class="text-lg">${t.message}</p>
        </div>

        <div class="mb-5">
            <div class="subsection">
                <div class="etiqueta">${T("Surname and forename")}</div>
                <div class="text-xl font-semibold">${r.fullName}</div>
            </div>
            <div class="subsection">
                <div class="etiqueta">${T("Date of birth")}</div>
                <div class="text-xl font-semibold">${r.dateOfBirth}</div>
            </div>
        </div>
           
        `}});
//# sourceMappingURL=DisplayHcert.93abcb69.js.map
