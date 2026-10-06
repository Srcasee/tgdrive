import axios from "axios";
export const api=axios.create({baseURL:"/",withCredentials:true});
api.interceptors.response.use(r=>r,e=>{if(e.response?.status===401) window.dispatchEvent(new Event("tgdrive:unauthorized")); return Promise.reject(e)});
export const auth={me:()=>api.get("/auth/me"),login:(data:any)=>api.post("/auth/login",data),logout:()=>api.post("/auth/logout")};
export const catalog={list:(params:any)=>api.get("/catalog",{params}),search:(params:any)=>api.get("/catalog/search",{params}),detail:(id:number)=>api.get("/catalog/"+id)};
export const admin={
 categories:()=>api.get("/api/admin/categories"),
 createCategory:(name:string)=>api.post("/api/admin/categories",{name}),
 updateCategory:(id:number,name:string)=>api.put("/api/admin/categories/"+id,{name}),
 deleteCategory:(id:number)=>api.delete("/api/admin/categories/"+id),
 setResourceCategories:(id:number,category_ids:number[])=>api.put("/api/admin/resources/"+id+"/categories",{category_ids}),
 downloads:()=>api.get("/api/admin/downloads/history"),
 activeDownloads:()=>api.get("/api/admin/downloads/active"),
 deleteDownload:(id:number)=>api.delete("/api/admin/downloads/"+id)
};
export const telegram={
 accounts:()=>api.get("/api/telegram/accounts"),
 accountEnabled:(id:number,enabled:boolean)=>api.put("/api/telegram/accounts/"+id+"/enabled",{enabled}),
 dialogs:(id:number)=>api.get("/api/telegram/accounts/"+id+"/dialogs"),
 deleteDialog:(id:number,chat:number)=>api.delete("/api/telegram/accounts/"+id+"/dialogs/"+chat),
 sources:()=>api.get("/api/telegram/sources"),
 createSource:(data:any)=>api.post("/api/telegram/sources",data),
 sourceEnabled:(id:number,enabled:boolean)=>api.put("/api/telegram/sources/"+id+"/enabled",{enabled}),
 deleteSource:(id:number)=>api.delete("/api/telegram/sources/"+id),
 reconnect:()=>api.post("/api/telegram/reconnect"),
 reconcile:()=>api.post("/api/telegram/reconcile")
};