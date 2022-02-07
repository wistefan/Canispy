import{r as c,A as l}from"./app.a68c96d4.js";import{a as i}from"./camerainfo.4311a7fd.js";import"./vendor.f8864ac5.js";c("SelectCamera",class extends l{constructor(e){super(e)}async enter(){let e=this.html;try{var t=await i();if(t.videoDevices.length==0){this.render(e`<p>No camera available</p>`);return}var r=t.videoDevices}catch{this.render(e`<p>No camera available</p>`);return}let s=e`
        <h2 class="text-center text-lg font-semibold my-3">Select a camera</h2>

        <ul>
        ${r.map(a=>e`
            <li class="mx-4 my-2 shadow-md">
                <a @click=${()=>this.setCamera(a.deviceId)} href="javascript:void(0)">
                    <div class="flex p-3">
                    <p class="text-lg font-medium">${a.label}</p>
                    </div>
                </a>
            </li>`)}
        </ul>

        `;this.render(s)}async setCamera(e){console.log("Selecting camera",e),window.selectedCamera=e,localStorage.setItem("selectedCamera",e),window.history.back()}});
//# sourceMappingURL=SelectCamera.29e08a80.js.map
