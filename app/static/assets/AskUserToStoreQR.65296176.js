import{r as n,A as o,l as s}from"./app.a68c96d4.js";import{C as l,v as d}from"./verifications.3e2b6b33.js";import"./vendor.f8864ac5.js";import"./_commonjsHelpers.4e997714.js";n("AskUserToStoreQR",class extends o{constructor(i){super(i)}async enter(i){let e=this.html,t=await this.verifyQRCertificate(i);if(t.result=="ERROR"){this.render(e`
            <div class="container center">
                <div id="hcertFailed" class="w3-panel bkg-error ptb-16">
                    <h3>Failed!</h3>
                    <p>${t.message}.</p>
                </div>

                <div class="ptb-16">
        
                    <button class="btn-primary" @click=${()=>window.location.replace(location.origin)}>${T("Cancel")}</button>
        
                </div>
            </div>
                `);return}this.QRCertificate=i;let r=e`
        <div class="container">
            <div class="w3-card-4 w3-center" style="margin-top:100px;">
        
                <header class="w3-container color-primary" style="padding:10px">
                    <h1>${T("You received a new EU COVID certificate!")}</h1>
                </header>
        
                <div class="w3-container ptb-16">
                    <p>${T("You can save it in this device for easy access later.")}</p>
                    <p>${T("Please click Save to save the certificate.")}</p>
                </div>
        
                <div class="ptb-16">
        
                    <button class="btn-primary" @click=${()=>this.saveQRCertificate()}>${T("Save")}</button>
        
                </div>
        
            </div>
        </div>
        `;this.render(r)}async verifyQRCertificate(i){let e;try{e=await l.decodeHC1QR(i,!0)}catch(c){return s.error("Error verifying credential",c),{result:"ERROR",message:T("Signature validation failed. The certificate is not valid.")}}let t=e[3];if(t==!1)return s.error("Error verifying credential"),{result:"ERROR",message:T("Signature validation failed. The certificate is not valid.")};console.log("Additional verifications");let r=d(e);if(console.log(r),r!=!0)return{result:"ERROR",message:T(r)};let a={result:"OK",hcert:e,message:T("The certificate is valid.")};return t==="PRE"&&(a.result="WARNING",a.message=T("$warningmsg")),a}saveQRCertificate(){window.localStorage.setItem("MYEUDCC",this.QRCertificate),window.location.replace(document.location.origin)}});
//# sourceMappingURL=AskUserToStoreQR.65296176.js.map
