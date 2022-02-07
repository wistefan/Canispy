var x=Object.defineProperty;var B=(s,e,t)=>e in s?x(s,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):s[e]=t;var d=(s,e,t)=>(B(s,typeof e!="symbol"?e+"":e,t),t);import{r as L,A as N,_ as j,l as y,g as C}from"./app.a68c96d4.js";import{g as O,a as V}from"./camerainfo.4311a7fd.js";import{h as E}from"./vendor.f8864ac5.js";const R=0,F=1,z=2,M=3;L("ScanQrPage",class extends N{constructor(e){super(e);d(this,"displayPage");d(this,"detectionInterval",200);d(this,"videoElement",{});d(this,"nativeBarcodeDetector");d(this,"zxingReader");d(this,"lastUsedCameraId");d(this,"canvasElement");d(this,"canvasSpace");"BarcodeDetector"in window?(console.log("Barcode Detector supported!"),this.nativeBarcodeDetector=new BarcodeDetector({formats:["qr_code"]})):(console.log("Barcode Detector is not supported by this browser."),this.zxingPromise=j(()=>import("./index.ac73f18e.js"),[])),this.videoElement={},this.canvasElement=document.createElement("canvas"),this.canvasSpace=this.canvasElement.getContext("2d")}async enter(e){if(e||(e="DisplayHcert"),this.displayPage=e,!this.nativeBarcodeDetector){let o=await this.zxingPromise;this.zxingReader=new o.BrowserQRCodeReader}this.lastUsedCameraId=await this.selectCamera();let t=E`
        <video ref=${this.videoElement} oncanPlay=${()=>this.canPlay()}></video>
        `;this.render(t);let a;this.lastUsedCameraId?(console.log("Constraints with deviceID:",this.lastUsedCameraId),a={audio:!1,video:{deviceId:this.lastUsedCameraId}}):(console.log("Constraints without camera"),a={audio:!1,video:{facingMode:"environment"}});let n;try{n=await navigator.mediaDevices.getUserMedia(a);let o=n.getVideoTracks();for(let c=0;c<o.length;c++){let m=o[c].getCapabilities();console.log(m)}this.videoElement.current.setAttribute("autoplay","true"),this.videoElement.current.setAttribute("muted","true"),this.videoElement.current.setAttribute("playsinline","true"),this.videoElement.current.srcObject=n,console.log(n)}catch(o){y.error("Error getting stream",o),this.render(this.messageErrorGettingStream());return}}async selectCamera(){var e=localStorage.getItem("selectedCamera");if(console.log("User selected camera:",e),e||(e=this.lastUsedCameraId,console.log("Last used camera:",e)),!e&&O()=="Android"){console.log("We are in Andoid and this is the first time");let t;try{t=await V(),console.log("Video devices in Android:",t)}catch(a){y.error("Error requesting camera access",a)}t&&t.defaultPreferredCamera&&(e=t.defaultPreferredCamera.deviceId,console.log("Selected camera in Android:",e)),e||console.log("In Android and no selected camera")}return e}async canPlay(){console.log("Video can play, try to detect QR"),this.videoElement.current.style.display="block",this.videoElement.current.play(),this.detectCode()}async detectCode(){let e=R,t;if(this.nativeBarcodeDetector){let a;try{a=await this.nativeBarcodeDetector.detect(this.videoElement.current)}catch{y.error(err);return}if(a.length===0){setTimeout(()=>this.detectCode(),this.detectionInterval);return}for(const n of a)if(console.log(n),t=n.rawValue,e=this.detectQRtype(t),e!=R)break}else{try{t=(await this.zxingReader.decodeOnceFromVideoElement(this.videoElement.current)).text,console.log("RESULT",t)}catch(a){y.error("ZXING decoding error",a)}e=this.detectQRtype(t)}if(e===R){setTimeout(()=>this.detectCode(),this.detectionInterval);return}if(e===M)return console.log("Going to ",this.displayPage),C(this.displayPage,t),!0}async exit(){!this.videoElement.current||(this.videoElement.current.style.display="none",this.videoElement.current.srcObject!==void 0&&this.videoElement.current.srcObject.getVideoTracks().forEach(e=>{e.stop()}))}detectQRtype(e){return!e||!e.startsWith?(y.error("detectQRtype: data is not string"),R):e.startsWith("HC1:")?M:e.startsWith("multi|w3cvc|")?z:e.startsWith("https")?F:R}errorMessage(e,t){return E`
        <div class="container">
            <div class="w3-card-4 center" style="margin-top:100px;">
        
                <header class="container color-primary" style="padding:10px">
                    <h1>${e}</h1>
                </header>
        
                <div class="container ptb-16">
                    <p>${t}</p>
                    <p>${T("Please click Accept to refresh the page.")}</p>
                </div>
        
                <div class="ptb-16">
        
                    <button class="btn-primary" @click=${()=>window.location.reload()}>${T("Accept")}</button>
        
                </div>
        
            </div>
        </div>
        `}messageErrorGettingStream(){return E`
        <div class="container">
            <div class="w3-card-4 center" style="margin-top:100px;">
        
                <header class="container color-primary" style="padding:10px">
                    <h1>${T("Error getting video stream")}</h1>
                </header>
        
                <div class="container ptb-16">
                    <p>${T("There was an error trying to start the camera.")}</p>
                    <p>${T("Please click Accept to refresh the page.")}</p>
                </div>
        
                <div class="ptb-16">
        
                    <button class="btn-primary" @click=${()=>window.location.reload()}>${T("Accept")}</button>
        
                </div>
        
            </div>
        </div>
        `}messageNoCameraPermissions(){return E`
        <div class="container">
            <div class="w3-card-4 center" style="margin-top:100px;">
        
                <header class="container color-primary" style="padding:10px">
                    <h1>${T("No camera access")}</h1>
                </header>
        
                <div class="container ptb-16">
                    <p>${T("You need to allow camera access to be able to scan a QR.")}</p>
                    <p>${T("Please click Accept to refresh the page.")}</p>
                </div>
        
                <div class="ptb-16">
        
                    <button class="btn-primary" @click=${()=>window.location.reload()}>${T("Accept")}</button>
        
                </div>
        
            </div>
        </div>
        `}});var r={callerPage:"",canvasElement:"",canvas:"",progressMessages:"",displayQRPage:"",callerType:"",receivedQRPieces:[],receivedPieces:"",video:"",myStream:""};async function ae(s,e,t,a){var n="";window.history.state!=null&&(n=window.history.state.pageName),r.callerPage=n,r.canvasElement=s,r.progressMessages=e,r.displayQRPage=t,r.callerType=a,r.receivedQRPieces=[],r.receivedPieces=new Set,r.canvas=r.canvasElement.getContext("2d"),r.video=document.createElement("video"),r.canvasElement.hidden=!0,r.progressMessages.innerText="Waiting for QR .........",navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"}}).then(function(o){r.myStream=o,r.video.srcObject=o,r.video.setAttribute("playsinline",!0),r.video.play(),requestAnimationFrame(h)})}async function h(){try{var s=r.video,e=r.canvas,t=r.canvasElement,a=r.receivedPieces,n=r.receivedQRPieces,o=r.progressMessages,c=r.myStream,m=r.callerType,$=r.callerPage,w=r.displayQRPage,Q="";if(window.history.state!=null&&(Q=window.history.state.pageName),Q!=$){stopMediaTracks(c);return}if(s.readyState!==s.HAVE_ENOUGH_DATA){requestAnimationFrame(h);return}t.hidden=!1,t.height=s.videoHeight,t.width=s.videoWidth;let p=s.videoWidth,k=s.videoHeight;e.drawImage(s,0,0,p,k);var A=e.getImageData(0,0,p,k);try{var l=jsQR(A.data,A.width,A.height,{inversionAttempts:"dontInvert"})}catch(i){console.error("jsQR:",i)}if(!l){requestAnimationFrame(h);return}var u=detectQRtype(l.data);if(u=="unknown"){requestAnimationFrame(h);return}if(u=="MultiJWT"){mylog("Scanned MultiJWT QR");var b=l.data.split("|"),P=b[2],v=b[3],W=b[4],H=P.charCodeAt(0),_=P.charCodeAt(1),S=v.charCodeAt(0),U=v.charCodeAt(1);if(H<48||H>57||_<48||_>57||S<48||S>57||U<48||U>57){requestAnimationFrame(h);return}if(a.has(v)){requestAnimationFrame(h);return}if(a.add(v),n[+v]=W,o.innerText="Received piece: "+v,a.size<P){requestAnimationFrame(h);return}stopMediaTracks(c),t.hidden=!0,mylog("Received all pieces",n);var I=n.join("");mylog("Received jwt",I);try{var D=decodeJWT(I);let i={type:"w3cvc",encoded:I,decoded:D};mylog("Writing current cred: ",i),await settingsPut("currentCredential",i)}catch(i){myerror(i),o.innerText=i;return}C(w,{screenType:m});return}if(u=="URL"){mylog("Scanned normal URL QR"),stopMediaTracks(c);let i=l.data.trim();if(i.startsWith(MYSELF)){const g=new URL(i);let f=g.searchParams.get("id");f?i=ISSUER_GET_CREDENTIAL+f:(f=g.searchParams.get("pubid"),f&&(i=ISSUER_GET_PUBLIC_CREDENTIAL+f))}await requestQRAndDisplay(i,w,m);return}const G=1,q=6,J=4,X=7,Y=-260;if(u=="HC1"){mylog("Scanned HC1 QR");let i=await CWT.decodeHC1QR(l.data);console.log("CWT.decodeHC1QR",i);let g={type:"hcert",encoded:l.data,decoded:i};await settingsPut("currentCredential",g),stopMediaTracks(c),C(w,{screenType:m});return}if(u=="Base64"){mylog("Scanned Base64 simple QR");let i=JSON.parse(atobUrl(l.data)),g={type:"ukimmigration",encoded:l.data,decoded:i};await settingsPut.setItem("currentCredential",g),stopMediaTracks(c),C(w,{screenType:m});return}}catch(p){stopMediaTracks(c),console.error(p),alert(`Error: ${p}`),C(homePage);return}}export{ae as initiateReceiveQRScanning};
//# sourceMappingURL=ScanQrPage.4ed618d3.js.map
