var fi={sword:{name:"\u9053\u6307\u5251",key:"Q",cooldown:.65,cost:0,damage:24,color:"#69b8ff",curls:[0,1.35,1.4,.04],thumb:1,spread:[-.08,0,0,.12]},guard:{name:"\u7834\u90AA\u5370",key:"E",cooldown:2.1,cost:0,damage:0,color:"#e6cb88",curls:[0,0,1.4,1.4],thumb:1,spread:[-.09,.11,0,0]},thunder:{name:"\u4E94\u96F7\u8BC0",key:"R",cooldown:3.2,cost:35,damage:100,color:"#ffb342",curls:[1.45,1.45,1.5,1.5],thumb:1.3,spread:[0,0,0,0]}};var mf=0,Bh=1,gf=2;var Ds=1,xf=2,Rr=3,wi=0,qt=1,st=2,Xn=0,Ir=1,dt=2,kh=3,zh=4,_f=5;var Us=100,yf=101,vf=102,Mf=103,Sf=104,bf=200,Tf=201,wf=202,Af=203,Gh=204,Vh=205,Ef=206,Cf=207,Rf=208,If=209,Pf=210,Lf=211,Nf=212,Df=213,Uf=214,Yo=0,Ko=1,Zo=2,pr=3,Jo=4,$o=5,jo=6,Qo=7,Hh=0,Ff=1,Of=2,ri=0,Oa=1,Ba=2,ka=3,Fs=4,za=5,Ga=6,Va=7,bh="attached",Bf="detached",Wh=300,us=301,Os=302,Pr=303,Sl=304,Ha=306,_i=1e3,rn=1001,mr=1002,Wt=1003,bl=1004;var Bs=1005;var Xt=1006,Lr=1007;var ai=1008;var bn=1009,Xh=1010,qh=1011,Nr=1012,Tl=1013,oi=1014,Dn=1015,an=1016,wl=1017,Al=1018,Dr=1020,Yh=35902,Kh=35899,Zh=1021,Jh=1022,Un=1023,yi=1026,ds=1027,El=1028,Cl=1029,fs=1030,Rl=1031;var Il=1033,Wa=33776,Xa=33777,qa=33778,Ya=33779,Pl=35840,Ll=35841,Nl=35842,Dl=35843,Ul=36196,Fl=37492,Ol=37496,Bl=37488,kl=37489,Ka=37490,zl=37491,Gl=37808,Vl=37809,Hl=37810,Wl=37811,Xl=37812,ql=37813,Yl=37814,Kl=37815,Zl=37816,Jl=37817,$l=37818,jl=37819,Ql=37820,ec=37821,tc=36492,nc=36494,ic=36495,sc=36283,rc=36284,Za=36285,ac=36286;var Ts=2300,ws=2301,Wo=2302,Th=2303,wh=2400,Ah=2401,Eh=2402,kf=2500;var $h=0,Ja=1,Ur=2,zf=3200;var oc=0,Gf=1,Xi="",Ct="srgb",gn="srgb-linear",aa="linear",_t="srgb";var Xo=7680;var Vf=519,Hf=512,Wf=513,Xf=514,lc=515,qf=516,Yf=517,cc=518,Kf=519,jh=35044,Qh=35048;var eu="300 es",ni=2e3,gr=2001;function Nm(s){for(let e=s.length-1;e>=0;--e)if(s[e]>=65535)return!0;return!1}function Dm(s){return ArrayBuffer.isView(s)&&!(s instanceof DataView)}function xr(s){return document.createElementNS("http://www.w3.org/1999/xhtml",s)}function Zf(){let s=xr("canvas");return s.style.display="block",s}var bd={},_r=null;function oa(...s){let e="THREE."+s.shift();_r?_r("log",e,...s):console.log(e,...s)}function Jf(s){let e=s[0];if(typeof e=="string"&&e.startsWith("TSL:")){let t=s[1];t&&t.isStackTrace?s[0]+=" "+t.getLocation():s[1]='Stack trace not available. Enable "THREE.Node.captureStackTrace" to capture stack traces.'}return s}function Le(...s){s=Jf(s);let e="THREE."+s.shift();if(_r)_r("warn",e,...s);else{let t=s[0];t&&t.isStackTrace?console.warn(t.getError(e)):console.warn(e,...s)}}function He(...s){s=Jf(s);let e="THREE."+s.shift();if(_r)_r("error",e,...s);else{let t=s[0];t&&t.isStackTrace?console.error(t.getError(e)):console.error(e,...s)}}function bs(...s){let e=s.join(" ");e in bd||(bd[e]=!0,Le(...s))}function $f(s,e,t){return new Promise(function(n,i){function r(){switch(s.clientWaitSync(e,s.SYNC_FLUSH_COMMANDS_BIT,0)){case s.WAIT_FAILED:i();break;case s.TIMEOUT_EXPIRED:setTimeout(r,t);break;default:n()}}setTimeout(r,t)})}var jf={[Yo]:Ko,[Zo]:jo,[Jo]:Qo,[pr]:$o,[Ko]:Yo,[jo]:Zo,[Qo]:Jo,[$o]:pr},vi=class{addEventListener(e,t){this._listeners===void 0&&(this._listeners={});let n=this._listeners;n[e]===void 0&&(n[e]=[]),n[e].indexOf(t)===-1&&n[e].push(t)}hasEventListener(e,t){let n=this._listeners;return n===void 0?!1:n[e]!==void 0&&n[e].indexOf(t)!==-1}removeEventListener(e,t){let n=this._listeners;if(n===void 0)return;let i=n[e];if(i!==void 0){let r=i.indexOf(t);r!==-1&&i.splice(r,1)}}dispatchEvent(e){let t=this._listeners;if(t===void 0)return;let n=t[e.type];if(n!==void 0){e.target=this;let i=n.slice(0);for(let r=0,a=i.length;r<a;r++)i[r].call(this,e);e.target=null}}},cn=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],Td=1234567,dr=Math.PI/180,As=180/Math.PI;function kn(){let s=Math.random()*4294967295|0,e=Math.random()*4294967295|0,t=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return(cn[s&255]+cn[s>>8&255]+cn[s>>16&255]+cn[s>>24&255]+"-"+cn[e&255]+cn[e>>8&255]+"-"+cn[e>>16&15|64]+cn[e>>24&255]+"-"+cn[t&63|128]+cn[t>>8&255]+"-"+cn[t>>16&255]+cn[t>>24&255]+cn[n&255]+cn[n>>8&255]+cn[n>>16&255]+cn[n>>24&255]).toLowerCase()}function ot(s,e,t){return Math.max(e,Math.min(t,s))}function tu(s,e){return(s%e+e)%e}function Um(s,e,t,n,i){return n+(s-e)*(i-n)/(t-e)}function Fm(s,e,t){return s!==e?(t-s)/(e-s):0}function ia(s,e,t){return(1-t)*s+t*e}function Om(s,e,t,n){return ia(s,e,1-Math.exp(-t*n))}function Bm(s,e=1){return e-Math.abs(tu(s,e*2)-e)}function km(s,e,t){return s<=e?0:s>=t?1:(s=(s-e)/(t-e),s*s*(3-2*s))}function zm(s,e,t){return s<=e?0:s>=t?1:(s=(s-e)/(t-e),s*s*s*(s*(s*6-15)+10))}function Gm(s,e){return s+Math.floor(Math.random()*(e-s+1))}function Vm(s,e){return s+Math.random()*(e-s)}function Hm(s){return s*(.5-Math.random())}function Wm(s){s!==void 0&&(Td=s);let e=Td+=1831565813;return e=Math.imul(e^e>>>15,e|1),e^=e+Math.imul(e^e>>>7,e|61),((e^e>>>14)>>>0)/4294967296}function Xm(s){return s*dr}function qm(s){return s*As}function Ym(s){return s>0&&Number.isInteger(s)&&2**Math.round(Math.log2(s))===s}function Km(s){return Math.pow(2,Math.ceil(Math.log(s)/Math.LN2))}function Zm(s){return Math.pow(2,Math.floor(Math.log(s)/Math.LN2))}function Jm(s,e,t,n,i){let r=Math.cos,a=Math.sin,o=r(t/2),c=a(t/2),l=r((e+n)/2),h=a((e+n)/2),u=r((e-n)/2),d=a((e-n)/2),p=r((n-e)/2),g=a((n-e)/2);switch(i){case"XYX":s.set(o*h,c*u,c*d,o*l);break;case"YZY":s.set(c*d,o*h,c*u,o*l);break;case"ZXZ":s.set(c*u,c*d,o*h,o*l);break;case"XZX":s.set(o*h,c*g,c*p,o*l);break;case"YXY":s.set(c*p,o*h,c*g,o*l);break;case"ZYZ":s.set(c*g,c*p,o*h,o*l);break;default:Le("MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+i)}}function ti(s,e){switch(e.constructor){case Float32Array:return s;case Uint32Array:return s/4294967295;case Uint16Array:return s/65535;case Uint8Array:case Uint8ClampedArray:return s/255;case Int32Array:return Math.max(s/2147483647,-1);case Int16Array:return Math.max(s/32767,-1);case Int8Array:return Math.max(s/127,-1);default:throw new Error("THREE.MathUtils: Invalid component type.")}}function wt(s,e){switch(e.constructor){case Float32Array:return s;case Uint32Array:return Math.round(s*4294967295);case Uint16Array:return Math.round(s*65535);case Uint8Array:case Uint8ClampedArray:return Math.round(s*255);case Int32Array:return Math.round(s*2147483647);case Int16Array:return Math.round(s*32767);case Int8Array:return Math.round(s*127);default:throw new Error("THREE.MathUtils: Invalid component type.")}}var kt={DEG2RAD:dr,RAD2DEG:As,generateUUID:kn,clamp:ot,euclideanModulo:tu,mapLinear:Um,inverseLerp:Fm,lerp:ia,damp:Om,pingpong:Bm,smoothstep:km,smootherstep:zm,randInt:Gm,randFloat:Vm,randFloatSpread:Hm,seededRandom:Wm,degToRad:Xm,radToDeg:qm,isPowerOfTwo:Ym,ceilPowerOfTwo:Km,floorPowerOfTwo:Zm,setQuaternionFromProperEuler:Jm,normalize:wt,denormalize:ti},ne=class s{static{s.prototype.isVector2=!0}constructor(e=0,t=0){this.x=e,this.y=t}get width(){return this.x}set width(e){this.x=e}get height(){return this.y}set height(e){this.y=e}set(e,t){return this.x=e,this.y=t,this}setScalar(e){return this.x=e,this.y=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;default:throw new Error("THREE.Vector2: index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;default:throw new Error("THREE.Vector2: index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y)}copy(e){return this.x=e.x,this.y=e.y,this}add(e){return this.x+=e.x,this.y+=e.y,this}addScalar(e){return this.x+=e,this.y+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this}subScalar(e){return this.x-=e,this.y-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this}multiply(e){return this.x*=e.x,this.y*=e.y,this}multiplyScalar(e){return this.x*=e,this.y*=e,this}divide(e){return this.x/=e.x,this.y/=e.y,this}divideScalar(e){return this.multiplyScalar(1/e)}applyMatrix3(e){let t=this.x,n=this.y,i=e.elements;return this.x=i[0]*t+i[3]*n+i[6],this.y=i[1]*t+i[4]*n+i[7],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this}clamp(e,t){return this.x=ot(this.x,e.x,t.x),this.y=ot(this.y,e.y,t.y),this}clampScalar(e,t){return this.x=ot(this.x,e,t),this.y=ot(this.y,e,t),this}clampLength(e,t){let n=this.length();return this.divideScalar(n||1).multiplyScalar(ot(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(e){return this.x*e.x+this.y*e.y}cross(e){return this.x*e.y-this.y*e.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(e){let t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;let n=this.dot(e)/t;return Math.acos(ot(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){let t=this.x-e.x,n=this.y-e.y;return t*t+n*n}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this}equals(e){return e.x===this.x&&e.y===this.y}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this}rotateAround(e,t){let n=Math.cos(t),i=Math.sin(t),r=this.x-e.x,a=this.y-e.y;return this.x=r*n-a*i+e.x,this.y=r*i+a*n+e.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}},nn=class{constructor(e=0,t=0,n=0,i=1){this.isQuaternion=!0,this._x=e,this._y=t,this._z=n,this._w=i}static slerpFlat(e,t,n,i,r,a,o){let c=n[i+0],l=n[i+1],h=n[i+2],u=n[i+3],d=r[a+0],p=r[a+1],g=r[a+2],v=r[a+3];if(u!==v||c!==d||l!==p||h!==g){let f=c*d+l*p+h*g+u*v;f<0&&(d=-d,p=-p,g=-g,v=-v,f=-f);let m=1-o;if(f<.9995){let _=Math.acos(f),b=Math.sin(_);m=Math.sin(m*_)/b,o=Math.sin(o*_)/b,c=c*m+d*o,l=l*m+p*o,h=h*m+g*o,u=u*m+v*o}else{c=c*m+d*o,l=l*m+p*o,h=h*m+g*o,u=u*m+v*o;let _=1/Math.sqrt(c*c+l*l+h*h+u*u);c*=_,l*=_,h*=_,u*=_}}e[t]=c,e[t+1]=l,e[t+2]=h,e[t+3]=u}static multiplyQuaternionsFlat(e,t,n,i,r,a){let o=n[i],c=n[i+1],l=n[i+2],h=n[i+3],u=r[a],d=r[a+1],p=r[a+2],g=r[a+3];return e[t]=o*g+h*u+c*p-l*d,e[t+1]=c*g+h*d+l*u-o*p,e[t+2]=l*g+h*p+o*d-c*u,e[t+3]=h*g-o*u-c*d-l*p,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,t,n,i){return this._x=e,this._y=t,this._z=n,this._w=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,t=!0){let n=e._x,i=e._y,r=e._z,a=e._order,o=Math.cos,c=Math.sin,l=o(n/2),h=o(i/2),u=o(r/2),d=c(n/2),p=c(i/2),g=c(r/2);switch(a){case"XYZ":this._x=d*h*u+l*p*g,this._y=l*p*u-d*h*g,this._z=l*h*g+d*p*u,this._w=l*h*u-d*p*g;break;case"YXZ":this._x=d*h*u+l*p*g,this._y=l*p*u-d*h*g,this._z=l*h*g-d*p*u,this._w=l*h*u+d*p*g;break;case"ZXY":this._x=d*h*u-l*p*g,this._y=l*p*u+d*h*g,this._z=l*h*g+d*p*u,this._w=l*h*u-d*p*g;break;case"ZYX":this._x=d*h*u-l*p*g,this._y=l*p*u+d*h*g,this._z=l*h*g-d*p*u,this._w=l*h*u+d*p*g;break;case"YZX":this._x=d*h*u+l*p*g,this._y=l*p*u+d*h*g,this._z=l*h*g-d*p*u,this._w=l*h*u-d*p*g;break;case"XZY":this._x=d*h*u-l*p*g,this._y=l*p*u-d*h*g,this._z=l*h*g+d*p*u,this._w=l*h*u+d*p*g;break;default:Le("Quaternion: .setFromEuler() encountered an unknown order: "+a)}return t===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,t){let n=t/2,i=Math.sin(n);return this._x=e.x*i,this._y=e.y*i,this._z=e.z*i,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(e){let t=e.elements,n=t[0],i=t[4],r=t[8],a=t[1],o=t[5],c=t[9],l=t[2],h=t[6],u=t[10],d=n+o+u;if(d>0){let p=.5/Math.sqrt(d+1);this._w=.25/p,this._x=(h-c)*p,this._y=(r-l)*p,this._z=(a-i)*p}else if(n>o&&n>u){let p=2*Math.sqrt(1+n-o-u);this._w=(h-c)/p,this._x=.25*p,this._y=(i+a)/p,this._z=(r+l)/p}else if(o>u){let p=2*Math.sqrt(1+o-n-u);this._w=(r-l)/p,this._x=(i+a)/p,this._y=.25*p,this._z=(c+h)/p}else{let p=2*Math.sqrt(1+u-n-o);this._w=(a-i)/p,this._x=(r+l)/p,this._y=(c+h)/p,this._z=.25*p}return this._onChangeCallback(),this}setFromUnitVectors(e,t){let n=e.dot(t)+1;return n<1e-8?(n=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=n):(this._x=0,this._y=-e.z,this._z=e.y,this._w=n)):(this._x=e.y*t.z-e.z*t.y,this._y=e.z*t.x-e.x*t.z,this._z=e.x*t.y-e.y*t.x,this._w=n),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(ot(this.dot(e),-1,1)))}rotateTowards(e,t){let n=this.angleTo(e);if(n===0)return this;let i=Math.min(1,t/n);return this.slerp(e,i),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,t){let n=e._x,i=e._y,r=e._z,a=e._w,o=t._x,c=t._y,l=t._z,h=t._w;return this._x=n*h+a*o+i*l-r*c,this._y=i*h+a*c+r*o-n*l,this._z=r*h+a*l+n*c-i*o,this._w=a*h-n*o-i*c-r*l,this._onChangeCallback(),this}slerp(e,t){let n=e._x,i=e._y,r=e._z,a=e._w,o=this.dot(e);o<0&&(n=-n,i=-i,r=-r,a=-a,o=-o);let c=1-t;if(o<.9995){let l=Math.acos(o),h=Math.sin(l);c=Math.sin(c*l)/h,t=Math.sin(t*l)/h,this._x=this._x*c+n*t,this._y=this._y*c+i*t,this._z=this._z*c+r*t,this._w=this._w*c+a*t,this._onChangeCallback()}else this._x=this._x*c+n*t,this._y=this._y*c+i*t,this._z=this._z*c+r*t,this._w=this._w*c+a*t,this.normalize();return this}slerpQuaternions(e,t,n){return this.copy(e).slerp(t,n)}random(){let e=2*Math.PI*Math.random(),t=2*Math.PI*Math.random(),n=Math.random(),i=Math.sqrt(1-n),r=Math.sqrt(n);return this.set(i*Math.sin(e),i*Math.cos(e),r*Math.sin(t),r*Math.cos(t))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,t=0){return this._x=e[t],this._y=e[t+1],this._z=e[t+2],this._w=e[t+3],this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._w,e}fromBufferAttribute(e,t){return this._x=e.getX(t),this._y=e.getY(t),this._z=e.getZ(t),this._w=e.getW(t),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}},R=class s{static{s.prototype.isVector3=!0}constructor(e=0,t=0,n=0){this.x=e,this.y=t,this.z=n}set(e,t,n){return n===void 0&&(n=this.z),this.x=e,this.y=t,this.z=n,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;default:throw new Error("THREE.Vector3: index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("THREE.Vector3: index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this}multiplyVectors(e,t){return this.x=e.x*t.x,this.y=e.y*t.y,this.z=e.z*t.z,this}applyEuler(e){return this.applyQuaternion(wd.setFromEuler(e))}applyAxisAngle(e,t){return this.applyQuaternion(wd.setFromAxisAngle(e,t))}applyMatrix3(e){let t=this.x,n=this.y,i=this.z,r=e.elements;return this.x=r[0]*t+r[3]*n+r[6]*i,this.y=r[1]*t+r[4]*n+r[7]*i,this.z=r[2]*t+r[5]*n+r[8]*i,this}applyNormalMatrix(e){return this.applyMatrix3(e).normalize()}applyMatrix4(e){let t=this.x,n=this.y,i=this.z,r=e.elements,a=1/(r[3]*t+r[7]*n+r[11]*i+r[15]);return this.x=(r[0]*t+r[4]*n+r[8]*i+r[12])*a,this.y=(r[1]*t+r[5]*n+r[9]*i+r[13])*a,this.z=(r[2]*t+r[6]*n+r[10]*i+r[14])*a,this}applyQuaternion(e){let t=this.x,n=this.y,i=this.z,r=e.x,a=e.y,o=e.z,c=e.w,l=2*(a*i-o*n),h=2*(o*t-r*i),u=2*(r*n-a*t);return this.x=t+c*l+a*u-o*h,this.y=n+c*h+o*l-r*u,this.z=i+c*u+r*h-a*l,this}project(e){return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix)}unproject(e){return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld)}transformDirection(e){let t=this.x,n=this.y,i=this.z,r=e.elements;return this.x=r[0]*t+r[4]*n+r[8]*i,this.y=r[1]*t+r[5]*n+r[9]*i,this.z=r[2]*t+r[6]*n+r[10]*i,this.normalize()}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this}divideScalar(e){return this.multiplyScalar(1/e)}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this}clamp(e,t){return this.x=ot(this.x,e.x,t.x),this.y=ot(this.y,e.y,t.y),this.z=ot(this.z,e.z,t.z),this}clampScalar(e,t){return this.x=ot(this.x,e,t),this.y=ot(this.y,e,t),this.z=ot(this.z,e,t),this}clampLength(e,t){let n=this.length();return this.divideScalar(n||1).multiplyScalar(ot(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this}cross(e){return this.crossVectors(this,e)}crossVectors(e,t){let n=e.x,i=e.y,r=e.z,a=t.x,o=t.y,c=t.z;return this.x=i*c-r*o,this.y=r*a-n*c,this.z=n*o-i*a,this}projectOnVector(e){let t=e.lengthSq();if(t===0)return this.set(0,0,0);let n=e.dot(this)/t;return this.copy(e).multiplyScalar(n)}projectOnPlane(e){return Kc.copy(this).projectOnVector(e),this.sub(Kc)}reflect(e){return this.sub(Kc.copy(e).multiplyScalar(2*this.dot(e)))}angleTo(e){let t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;let n=this.dot(e)/t;return Math.acos(ot(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){let t=this.x-e.x,n=this.y-e.y,i=this.z-e.z;return t*t+n*n+i*i}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)+Math.abs(this.z-e.z)}setFromSpherical(e){return this.setFromSphericalCoords(e.radius,e.phi,e.theta)}setFromSphericalCoords(e,t,n){let i=Math.sin(t)*e;return this.x=i*Math.sin(n),this.y=Math.cos(t)*e,this.z=i*Math.cos(n),this}setFromCylindrical(e){return this.setFromCylindricalCoords(e.radius,e.theta,e.y)}setFromCylindricalCoords(e,t,n){return this.x=e*Math.sin(t),this.y=n,this.z=e*Math.cos(t),this}setFromMatrixPosition(e){let t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this}setFromMatrixScale(e){let t=this.setFromMatrixColumn(e,0).length(),n=this.setFromMatrixColumn(e,1).length(),i=this.setFromMatrixColumn(e,2).length();return this.x=t,this.y=n,this.z=i,this}setFromMatrixColumn(e,t){return this.fromArray(e.elements,t*4)}setFromMatrix3Column(e,t){return this.fromArray(e.elements,t*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(e){return this.x=e.r,this.y=e.g,this.z=e.b,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){let e=Math.random()*Math.PI*2,t=Math.random()*2-1,n=Math.sqrt(1-t*t);return this.x=n*Math.cos(e),this.y=t,this.z=n*Math.sin(e),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}},Kc=new R,wd=new nn,Ze=class s{static{s.prototype.isMatrix3=!0}constructor(e,t,n,i,r,a,o,c,l){this.elements=[1,0,0,0,1,0,0,0,1],e!==void 0&&this.set(e,t,n,i,r,a,o,c,l)}set(e,t,n,i,r,a,o,c,l){let h=this.elements;return h[0]=e,h[1]=i,h[2]=o,h[3]=t,h[4]=r,h[5]=c,h[6]=n,h[7]=a,h[8]=l,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(e){let t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],this}extractBasis(e,t,n){return e.setFromMatrix3Column(this,0),t.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(e){let t=e.elements;return this.set(t[0],t[4],t[8],t[1],t[5],t[9],t[2],t[6],t[10]),this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){let n=e.elements,i=t.elements,r=this.elements,a=n[0],o=n[3],c=n[6],l=n[1],h=n[4],u=n[7],d=n[2],p=n[5],g=n[8],v=i[0],f=i[3],m=i[6],_=i[1],b=i[4],x=i[7],T=i[2],S=i[5],A=i[8];return r[0]=a*v+o*_+c*T,r[3]=a*f+o*b+c*S,r[6]=a*m+o*x+c*A,r[1]=l*v+h*_+u*T,r[4]=l*f+h*b+u*S,r[7]=l*m+h*x+u*A,r[2]=d*v+p*_+g*T,r[5]=d*f+p*b+g*S,r[8]=d*m+p*x+g*A,this}multiplyScalar(e){let t=this.elements;return t[0]*=e,t[3]*=e,t[6]*=e,t[1]*=e,t[4]*=e,t[7]*=e,t[2]*=e,t[5]*=e,t[8]*=e,this}determinant(){let e=this.elements,t=e[0],n=e[1],i=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],h=e[8];return t*a*h-t*o*l-n*r*h+n*o*c+i*r*l-i*a*c}invert(){let e=this.elements,t=e[0],n=e[1],i=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],h=e[8],u=h*a-o*l,d=o*c-h*r,p=l*r-a*c,g=t*u+n*d+i*p;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);let v=1/g;return e[0]=u*v,e[1]=(i*l-h*n)*v,e[2]=(o*n-i*a)*v,e[3]=d*v,e[4]=(h*t-i*c)*v,e[5]=(i*r-o*t)*v,e[6]=p*v,e[7]=(n*c-l*t)*v,e[8]=(a*t-n*r)*v,this}transpose(){let e,t=this.elements;return e=t[1],t[1]=t[3],t[3]=e,e=t[2],t[2]=t[6],t[6]=e,e=t[5],t[5]=t[7],t[7]=e,this}getNormalMatrix(e){return this.setFromMatrix4(e).invert().transpose()}transposeIntoArray(e){let t=this.elements;return e[0]=t[0],e[1]=t[3],e[2]=t[6],e[3]=t[1],e[4]=t[4],e[5]=t[7],e[6]=t[2],e[7]=t[5],e[8]=t[8],this}setUvTransform(e,t,n,i,r,a,o){let c=Math.cos(r),l=Math.sin(r);return this.set(n*c,n*l,-n*(c*a+l*o)+a+e,-i*l,i*c,-i*(-l*a+c*o)+o+t,0,0,1),this}scale(e,t){return bs("Matrix3: .scale() is deprecated. Use .makeScale() instead."),this.premultiply(Zc.makeScale(e,t)),this}rotate(e){return bs("Matrix3: .rotate() is deprecated. Use .makeRotation() instead."),this.premultiply(Zc.makeRotation(-e)),this}translate(e,t){return bs("Matrix3: .translate() is deprecated. Use .makeTranslation() instead."),this.premultiply(Zc.makeTranslation(e,t)),this}makeTranslation(e,t){return e.isVector2?this.set(1,0,e.x,0,1,e.y,0,0,1):this.set(1,0,e,0,1,t,0,0,1),this}makeRotation(e){let t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,n,t,0,0,0,1),this}makeScale(e,t){return this.set(e,0,0,0,t,0,0,0,1),this}equals(e){let t=this.elements,n=e.elements;for(let i=0;i<9;i++)if(t[i]!==n[i])return!1;return!0}fromArray(e,t=0){for(let n=0;n<9;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){let n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e}clone(){return new this.constructor().fromArray(this.elements)}},Zc=new Ze,Ad=new Ze().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),Ed=new Ze().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function $m(){let s={enabled:!0,workingColorSpace:gn,spaces:{},convert:function(i,r,a){return this.enabled===!1||r===a||!r||!a||(this.spaces[r].transfer===_t&&(i.r=Fi(i.r),i.g=Fi(i.g),i.b=Fi(i.b)),this.spaces[r].primaries!==this.spaces[a].primaries&&(i.applyMatrix3(this.spaces[r].toXYZ),i.applyMatrix3(this.spaces[a].fromXYZ)),this.spaces[a].transfer===_t&&(i.r=fr(i.r),i.g=fr(i.g),i.b=fr(i.b))),i},workingToColorSpace:function(i,r){return this.convert(i,this.workingColorSpace,r)},colorSpaceToWorking:function(i,r){return this.convert(i,r,this.workingColorSpace)},getPrimaries:function(i){return this.spaces[i].primaries},getTransfer:function(i){return i===Xi?aa:this.spaces[i].transfer},getToneMappingMode:function(i){return this.spaces[i].outputColorSpaceConfig.toneMappingMode||"standard"},getLuminanceCoefficients:function(i,r=this.workingColorSpace){return i.fromArray(this.spaces[r].luminanceCoefficients)},define:function(i){Object.assign(this.spaces,i)},_getMatrix:function(i,r,a){return i.copy(this.spaces[r].toXYZ).multiply(this.spaces[a].fromXYZ)},_getDrawingBufferColorSpace:function(i){return this.spaces[i].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(i=this.workingColorSpace){return this.spaces[i].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(i,r){return bs("ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),s.workingToColorSpace(i,r)},toWorkingColorSpace:function(i,r){return bs("ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),s.colorSpaceToWorking(i,r)}},e=[.64,.33,.3,.6,.15,.06],t=[.2126,.7152,.0722],n=[.3127,.329];return s.define({[gn]:{primaries:e,whitePoint:n,transfer:aa,toXYZ:Ad,fromXYZ:Ed,luminanceCoefficients:t,workingColorSpaceConfig:{unpackColorSpace:Ct},outputColorSpaceConfig:{drawingBufferColorSpace:Ct}},[Ct]:{primaries:e,whitePoint:n,transfer:_t,toXYZ:Ad,fromXYZ:Ed,luminanceCoefficients:t,outputColorSpaceConfig:{drawingBufferColorSpace:Ct}}}),s}var it=$m();function Fi(s){return s<.04045?s*.0773993808:Math.pow(s*.9478672986+.0521327014,2.4)}function fr(s){return s<.0031308?s*12.92:1.055*Math.pow(s,.41666)-.055}var Ks,el=class{static getDataURL(e,t="image/png"){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let n;if(e instanceof HTMLCanvasElement)n=e;else{Ks===void 0&&(Ks=xr("canvas")),Ks.width=e.width,Ks.height=e.height;let i=Ks.getContext("2d");e instanceof ImageData?i.putImageData(e,0,0):i.drawImage(e,0,0,e.width,e.height),n=Ks}return n.toDataURL(t)}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){let t=xr("canvas");t.width=e.width,t.height=e.height;let n=t.getContext("2d");n.drawImage(e,0,0,e.width,e.height);let i=n.getImageData(0,0,e.width,e.height),r=i.data;for(let a=0;a<r.length;a++)r[a]=Fi(r[a]/255)*255;return n.putImageData(i,0,0),t}else if(e.data){let t=e.data.slice(0);for(let n=0;n<t.length;n++)t instanceof Uint8Array||t instanceof Uint8ClampedArray?t[n]=Math.floor(Fi(t[n]/255)*255):t[n]=Fi(t[n]);return{data:t,width:e.width,height:e.height}}else return Le("ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}},jm=0,yr=class{constructor(e=null){this.isTextureSource=!0,Object.defineProperty(this,"id",{value:jm++}),this.uuid=kn(),this.data=e,this.dataReady=!0,this.version=0}getSize(e){let t=this.data;return typeof HTMLVideoElement<"u"&&t instanceof HTMLVideoElement?e.set(t.videoWidth,t.videoHeight,0):typeof VideoFrame<"u"&&t instanceof VideoFrame?e.set(t.displayWidth,t.displayHeight,0):t!==null?e.set(t.width,t.height,t.depth||0):e.set(0,0,0),e}set needsUpdate(e){e===!0&&this.version++}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.images[this.uuid]!==void 0)return e.images[this.uuid];let n={uuid:this.uuid,url:""},i=this.data;if(i!==null){let r;if(Array.isArray(i)){r=[];for(let a=0,o=i.length;a<o;a++)i[a].isDataTexture?r.push(Jc(i[a].image)):r.push(Jc(i[a]))}else r=Jc(i);n.url=r}return t||(e.images[this.uuid]=n),n}};function Jc(s){return typeof HTMLImageElement<"u"&&s instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&s instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&s instanceof ImageBitmap?el.getDataURL(s):s.data?{data:Array.from(s.data),width:s.width,height:s.height,type:s.data.constructor.name}:(Le("Texture: Unable to serialize Texture."),{})}var Qm=0,$c=new R,jt=class s extends vi{constructor(e=s.DEFAULT_IMAGE,t=s.DEFAULT_MAPPING,n=rn,i=rn,r=Xt,a=ai,o=Un,c=bn,l=s.DEFAULT_ANISOTROPY,h=Xi){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:Qm++}),this.uuid=kn(),this.name="",this.source=new yr(e),this.mipmaps=[],this.mapping=t,this.channel=0,this.wrapS=n,this.wrapT=i,this.magFilter=r,this.minFilter=a,this.anisotropy=l,this.format=o,this.internalFormat=null,this.type=c,this.offset=new ne(0,0),this.repeat=new ne(1,1),this.center=new ne(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new Ze,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=h,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(e&&e.depth&&e.depth>1),this.pmremVersion=0,this.normalized=!1}get width(){return this.source.getSize($c).x}get height(){return this.source.getSize($c).y}get depth(){return this.source.getSize($c).z}get image(){return this.source.data}set image(e){this.source.data=e}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(e){return this.name=e.name,this.source=e.source,this.mipmaps=e.mipmaps.slice(0),this.mapping=e.mapping,this.channel=e.channel,this.wrapS=e.wrapS,this.wrapT=e.wrapT,this.magFilter=e.magFilter,this.minFilter=e.minFilter,this.anisotropy=e.anisotropy,this.format=e.format,this.internalFormat=e.internalFormat,this.type=e.type,this.normalized=e.normalized,this.offset.copy(e.offset),this.repeat.copy(e.repeat),this.center.copy(e.center),this.rotation=e.rotation,this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrix.copy(e.matrix),this.generateMipmaps=e.generateMipmaps,this.premultiplyAlpha=e.premultiplyAlpha,this.flipY=e.flipY,this.unpackAlignment=e.unpackAlignment,this.colorSpace=e.colorSpace,this.renderTarget=e.renderTarget,this.isRenderTargetTexture=e.isRenderTargetTexture,this.isArrayTexture=e.isArrayTexture,this.userData=JSON.parse(JSON.stringify(e.userData)),this.needsUpdate=!0,this}setValues(e){for(let t in e){let n=e[t];if(n===void 0){Le(`Texture.setValues(): parameter '${t}' has value of undefined.`);continue}let i=this[t];if(i===void 0){Le(`Texture.setValues(): property '${t}' does not exist.`);continue}i&&n&&i.isVector2&&n.isVector2||i&&n&&i.isVector3&&n.isVector3||i&&n&&i.isMatrix3&&n.isMatrix3?i.copy(n):this[t]=n}}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.textures[this.uuid]!==void 0)return e.textures[this.uuid];let n={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(e).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,normalized:this.normalized,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),t||(e.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(e){if(this.mapping!==Wh)return e;if(e.applyMatrix3(this.matrix),e.x<0||e.x>1)switch(this.wrapS){case _i:e.x=e.x-Math.floor(e.x);break;case rn:e.x=e.x<0?0:1;break;case mr:Math.abs(Math.floor(e.x)%2)===1?e.x=Math.ceil(e.x)-e.x:e.x=e.x-Math.floor(e.x);break}if(e.y<0||e.y>1)switch(this.wrapT){case _i:e.y=e.y-Math.floor(e.y);break;case rn:e.y=e.y<0?0:1;break;case mr:Math.abs(Math.floor(e.y)%2)===1?e.y=Math.ceil(e.y)-e.y:e.y=e.y-Math.floor(e.y);break}return this.flipY&&(e.y=1-e.y),e}set needsUpdate(e){e===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(e){e===!0&&this.pmremVersion++}};jt.DEFAULT_IMAGE=null;jt.DEFAULT_MAPPING=Wh;jt.DEFAULT_ANISOTROPY=1;var At=class s{static{s.prototype.isVector4=!0}constructor(e=0,t=0,n=0,i=1){this.x=e,this.y=t,this.z=n,this.w=i}get width(){return this.z}set width(e){this.z=e}get height(){return this.w}set height(e){this.w=e}set(e,t,n,i){return this.x=e,this.y=t,this.z=n,this.w=i,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this.w=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setW(e){return this.w=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;case 3:this.w=t;break;default:throw new Error("THREE.Vector4: index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("THREE.Vector4: index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this.w=e.w!==void 0?e.w:1,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this.w+=e.w,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this.w+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this.w=e.w+t.w,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this.w+=e.w*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this.w-=e.w,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this.w-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this.w=e.w-t.w,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this.w*=e.w,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this.w*=e,this}applyMatrix4(e){let t=this.x,n=this.y,i=this.z,r=this.w,a=e.elements;return this.x=a[0]*t+a[4]*n+a[8]*i+a[12]*r,this.y=a[1]*t+a[5]*n+a[9]*i+a[13]*r,this.z=a[2]*t+a[6]*n+a[10]*i+a[14]*r,this.w=a[3]*t+a[7]*n+a[11]*i+a[15]*r,this}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this.w/=e.w,this}divideScalar(e){return this.multiplyScalar(1/e)}setAxisAngleFromQuaternion(e){this.w=2*Math.acos(e.w);let t=Math.sqrt(1-e.w*e.w);return t<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=e.x/t,this.y=e.y/t,this.z=e.z/t),this}setAxisAngleFromRotationMatrix(e){let t,n,i,r,c=e.elements,l=c[0],h=c[4],u=c[8],d=c[1],p=c[5],g=c[9],v=c[2],f=c[6],m=c[10];if(Math.abs(h-d)<.01&&Math.abs(u-v)<.01&&Math.abs(g-f)<.01){if(Math.abs(h+d)<.1&&Math.abs(u+v)<.1&&Math.abs(g+f)<.1&&Math.abs(l+p+m-3)<.1)return this.set(1,0,0,0),this;t=Math.PI;let b=(l+1)/2,x=(p+1)/2,T=(m+1)/2,S=(h+d)/4,A=(u+v)/4,y=(g+f)/4;return b>x&&b>T?b<.01?(n=0,i=.707106781,r=.707106781):(n=Math.sqrt(b),i=S/n,r=A/n):x>T?x<.01?(n=.707106781,i=0,r=.707106781):(i=Math.sqrt(x),n=S/i,r=y/i):T<.01?(n=.707106781,i=.707106781,r=0):(r=Math.sqrt(T),n=A/r,i=y/r),this.set(n,i,r,t),this}let _=Math.sqrt((f-g)*(f-g)+(u-v)*(u-v)+(d-h)*(d-h));return Math.abs(_)<.001&&(_=1),this.x=(f-g)/_,this.y=(u-v)/_,this.z=(d-h)/_,this.w=Math.acos((l+p+m-1)/2),this}setFromMatrixPosition(e){let t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this.w=t[15],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this.w=Math.min(this.w,e.w),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this.w=Math.max(this.w,e.w),this}clamp(e,t){return this.x=ot(this.x,e.x,t.x),this.y=ot(this.y,e.y,t.y),this.z=ot(this.z,e.z,t.z),this.w=ot(this.w,e.w,t.w),this}clampScalar(e,t){return this.x=ot(this.x,e,t),this.y=ot(this.y,e,t),this.z=ot(this.z,e,t),this.w=ot(this.w,e,t),this}clampLength(e,t){let n=this.length();return this.divideScalar(n||1).multiplyScalar(ot(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z+this.w*e.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this.w+=(e.w-this.w)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this.w=e.w+(t.w-e.w)*n,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z&&e.w===this.w}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this.w=e[t+3],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e[t+3]=this.w,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this.w=e.getW(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}},tl=class extends vi{constructor(e=1,t=1,n={}){super(),n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:Xt,depthBuffer:!0,stencilBuffer:!1,resolveColorBuffer:!0,resolveDepthBuffer:!0,resolveStencilBuffer:!0,storeMultisampledColorBuffer:!0,storeMultisampledDepthBuffer:!0,storeMultisampledStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1,useArrayDepthTexture:!1},n),this.isRenderTarget=!0,this.width=e,this.height=t,this.depth=n.depth,this.scissor=new At(0,0,e,t),this.scissorTest=!1,this.viewport=new At(0,0,e,t),this.textures=[];let i={width:e,height:t,depth:n.depth},r=new jt(i),a=n.count;for(let o=0;o<a;o++)this.textures[o]=r.clone(),this.textures[o].isRenderTargetTexture=!0,this.textures[o].renderTarget=this;this._setTextureOptions(n),this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.resolveColorBuffer=n.resolveColorBuffer,this.resolveDepthBuffer=n.resolveDepthBuffer,this.resolveStencilBuffer=n.resolveStencilBuffer,this.storeMultisampledColorBuffer=n.storeMultisampledColorBuffer,this.storeMultisampledDepthBuffer=n.storeMultisampledDepthBuffer,this.storeMultisampledStencilBuffer=n.storeMultisampledStencilBuffer,this._depthTexture=null,this.depthTexture=n.depthTexture,this.samples=n.samples,this.multiview=n.multiview,this.useArrayDepthTexture=n.useArrayDepthTexture}_setTextureOptions(e={}){let t={minFilter:Xt,generateMipmaps:!1,flipY:!1,internalFormat:null};e.mapping!==void 0&&(t.mapping=e.mapping),e.wrapS!==void 0&&(t.wrapS=e.wrapS),e.wrapT!==void 0&&(t.wrapT=e.wrapT),e.wrapR!==void 0&&(t.wrapR=e.wrapR),e.magFilter!==void 0&&(t.magFilter=e.magFilter),e.minFilter!==void 0&&(t.minFilter=e.minFilter),e.format!==void 0&&(t.format=e.format),e.type!==void 0&&(t.type=e.type),e.anisotropy!==void 0&&(t.anisotropy=e.anisotropy),e.colorSpace!==void 0&&(t.colorSpace=e.colorSpace),e.flipY!==void 0&&(t.flipY=e.flipY),e.generateMipmaps!==void 0&&(t.generateMipmaps=e.generateMipmaps),e.internalFormat!==void 0&&(t.internalFormat=e.internalFormat);for(let n=0;n<this.textures.length;n++)this.textures[n].setValues(t)}get texture(){return this.textures[0]}set texture(e){this.textures[0]=e}set depthTexture(e){this._depthTexture!==null&&this._depthTexture.renderTarget===this&&(this._depthTexture.renderTarget=null),e!==null&&e.renderTarget===null&&(e.renderTarget=this),this._depthTexture=e}get depthTexture(){return this._depthTexture}setSize(e,t,n=1){if(this.width!==e||this.height!==t||this.depth!==n){this.width=e,this.height=t,this.depth=n;for(let i=0,r=this.textures.length;i<r;i++)this.textures[i].image.width=e,this.textures[i].image.height=t,this.textures[i].image.depth=n,this.textures[i].isData3DTexture!==!0&&(this.textures[i].isArrayTexture=this.textures[i].image.depth>1);this.dispose()}this.viewport.set(0,0,e,t),this.scissor.set(0,0,e,t)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.textures.length=0;for(let t=0,n=e.textures.length;t<n;t++){this.textures[t]=e.textures[t].clone(),this.textures[t].isRenderTargetTexture=!0,this.textures[t].renderTarget=this;let i=Object.assign({},e.textures[t].image);this.textures[t].source=new yr(i)}if(this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,this.resolveColorBuffer=e.resolveColorBuffer,this.resolveDepthBuffer=e.resolveDepthBuffer,this.resolveStencilBuffer=e.resolveStencilBuffer,this.storeMultisampledColorBuffer=e.storeMultisampledColorBuffer,this.storeMultisampledDepthBuffer=e.storeMultisampledDepthBuffer,this.storeMultisampledStencilBuffer=e.storeMultisampledStencilBuffer,e.depthTexture!==null)if(e.depthTexture.renderTarget===e){let t=e.depthTexture.clone();t.renderTarget=null,this.depthTexture=t}else this.depthTexture=e.depthTexture;return this.samples=e.samples,this.multiview=e.multiview,this.useArrayDepthTexture=e.useArrayDepthTexture,this}dispose(){this.dispatchEvent({type:"dispose"})}},Jt=class extends tl{constructor(e=1,t=1,n={}){super(e,t,n),this.isWebGLRenderTarget=!0}},la=class extends jt{constructor(e=null,t=1,n=1,i=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:t,height:n,depth:i},this.magFilter=Wt,this.minFilter=Wt,this.wrapR=rn,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}copy(e){return super.copy(e),this.wrapR=e.wrapR,this}addLayerUpdate(e){this.layerUpdates.add(e)}clearLayerUpdates(){this.layerUpdates.clear()}};var nl=class extends jt{constructor(e=null,t=1,n=1,i=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:t,height:n,depth:i},this.magFilter=Wt,this.minFilter=Wt,this.wrapR=rn,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}copy(e){return super.copy(e),this.wrapR=e.wrapR,this}};var je=class s{static{s.prototype.isMatrix4=!0}constructor(e,t,n,i,r,a,o,c,l,h,u,d,p,g,v,f){this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],e!==void 0&&this.set(e,t,n,i,r,a,o,c,l,h,u,d,p,g,v,f)}set(e,t,n,i,r,a,o,c,l,h,u,d,p,g,v,f){let m=this.elements;return m[0]=e,m[4]=t,m[8]=n,m[12]=i,m[1]=r,m[5]=a,m[9]=o,m[13]=c,m[2]=l,m[6]=h,m[10]=u,m[14]=d,m[3]=p,m[7]=g,m[11]=v,m[15]=f,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new s().fromArray(this.elements)}copy(e){let t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],t[9]=n[9],t[10]=n[10],t[11]=n[11],t[12]=n[12],t[13]=n[13],t[14]=n[14],t[15]=n[15],this}copyPosition(e){let t=this.elements,n=e.elements;return t[12]=n[12],t[13]=n[13],t[14]=n[14],this}setFromMatrix3(e){let t=e.elements;return this.set(t[0],t[3],t[6],0,t[1],t[4],t[7],0,t[2],t[5],t[8],0,0,0,0,1),this}extractBasis(e,t,n){return this.determinantAffine()===0?(e.set(1,0,0),t.set(0,1,0),n.set(0,0,1),this):(e.setFromMatrixColumn(this,0),t.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this)}makeBasis(e,t,n){return this.set(e.x,t.x,n.x,0,e.y,t.y,n.y,0,e.z,t.z,n.z,0,0,0,0,1),this}extractRotation(e){if(e.determinantAffine()===0)return this.identity();let t=this.elements,n=e.elements,i=1/Zs.setFromMatrixColumn(e,0).length(),r=1/Zs.setFromMatrixColumn(e,1).length(),a=1/Zs.setFromMatrixColumn(e,2).length();return t[0]=n[0]*i,t[1]=n[1]*i,t[2]=n[2]*i,t[3]=0,t[4]=n[4]*r,t[5]=n[5]*r,t[6]=n[6]*r,t[7]=0,t[8]=n[8]*a,t[9]=n[9]*a,t[10]=n[10]*a,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromEuler(e){let t=this.elements,n=e.x,i=e.y,r=e.z,a=Math.cos(n),o=Math.sin(n),c=Math.cos(i),l=Math.sin(i),h=Math.cos(r),u=Math.sin(r);if(e.order==="XYZ"){let d=a*h,p=a*u,g=o*h,v=o*u;t[0]=c*h,t[4]=-c*u,t[8]=l,t[1]=p+g*l,t[5]=d-v*l,t[9]=-o*c,t[2]=v-d*l,t[6]=g+p*l,t[10]=a*c}else if(e.order==="YXZ"){let d=c*h,p=c*u,g=l*h,v=l*u;t[0]=d+v*o,t[4]=g*o-p,t[8]=a*l,t[1]=a*u,t[5]=a*h,t[9]=-o,t[2]=p*o-g,t[6]=v+d*o,t[10]=a*c}else if(e.order==="ZXY"){let d=c*h,p=c*u,g=l*h,v=l*u;t[0]=d-v*o,t[4]=-a*u,t[8]=g+p*o,t[1]=p+g*o,t[5]=a*h,t[9]=v-d*o,t[2]=-a*l,t[6]=o,t[10]=a*c}else if(e.order==="ZYX"){let d=a*h,p=a*u,g=o*h,v=o*u;t[0]=c*h,t[4]=g*l-p,t[8]=d*l+v,t[1]=c*u,t[5]=v*l+d,t[9]=p*l-g,t[2]=-l,t[6]=o*c,t[10]=a*c}else if(e.order==="YZX"){let d=a*c,p=a*l,g=o*c,v=o*l;t[0]=c*h,t[4]=v-d*u,t[8]=g*u+p,t[1]=u,t[5]=a*h,t[9]=-o*h,t[2]=-l*h,t[6]=p*u+g,t[10]=d-v*u}else if(e.order==="XZY"){let d=a*c,p=a*l,g=o*c,v=o*l;t[0]=c*h,t[4]=-u,t[8]=l*h,t[1]=d*u+v,t[5]=a*h,t[9]=p*u-g,t[2]=g*u-p,t[6]=o*h,t[10]=v*u+d}return t[3]=0,t[7]=0,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromQuaternion(e){return this.compose(eg,e,tg)}lookAt(e,t,n){let i=this.elements;return wn.subVectors(e,t),wn.lengthSq()===0&&(wn.z=1),wn.normalize(),ji.crossVectors(n,wn),ji.lengthSq()===0&&(Math.abs(n.z)===1?wn.x+=1e-4:wn.z+=1e-4,wn.normalize(),ji.crossVectors(n,wn)),ji.normalize(),ho.crossVectors(wn,ji),i[0]=ji.x,i[4]=ho.x,i[8]=wn.x,i[1]=ji.y,i[5]=ho.y,i[9]=wn.y,i[2]=ji.z,i[6]=ho.z,i[10]=wn.z,this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){let n=e.elements,i=t.elements,r=this.elements,a=n[0],o=n[4],c=n[8],l=n[12],h=n[1],u=n[5],d=n[9],p=n[13],g=n[2],v=n[6],f=n[10],m=n[14],_=n[3],b=n[7],x=n[11],T=n[15],S=i[0],A=i[4],y=i[8],E=i[12],I=i[1],L=i[5],F=i[9],V=i[13],D=i[2],B=i[6],X=i[10],W=i[14],re=i[3],q=i[7],j=i[11],te=i[15];return r[0]=a*S+o*I+c*D+l*re,r[4]=a*A+o*L+c*B+l*q,r[8]=a*y+o*F+c*X+l*j,r[12]=a*E+o*V+c*W+l*te,r[1]=h*S+u*I+d*D+p*re,r[5]=h*A+u*L+d*B+p*q,r[9]=h*y+u*F+d*X+p*j,r[13]=h*E+u*V+d*W+p*te,r[2]=g*S+v*I+f*D+m*re,r[6]=g*A+v*L+f*B+m*q,r[10]=g*y+v*F+f*X+m*j,r[14]=g*E+v*V+f*W+m*te,r[3]=_*S+b*I+x*D+T*re,r[7]=_*A+b*L+x*B+T*q,r[11]=_*y+b*F+x*X+T*j,r[15]=_*E+b*V+x*W+T*te,this}multiplyScalar(e){let t=this.elements;return t[0]*=e,t[4]*=e,t[8]*=e,t[12]*=e,t[1]*=e,t[5]*=e,t[9]*=e,t[13]*=e,t[2]*=e,t[6]*=e,t[10]*=e,t[14]*=e,t[3]*=e,t[7]*=e,t[11]*=e,t[15]*=e,this}determinant(){let e=this.elements,t=e[0],n=e[4],i=e[8],r=e[12],a=e[1],o=e[5],c=e[9],l=e[13],h=e[2],u=e[6],d=e[10],p=e[14],g=e[3],v=e[7],f=e[11],m=e[15],_=c*p-l*d,b=o*p-l*u,x=o*d-c*u,T=a*p-l*h,S=a*d-c*h,A=a*u-o*h;return t*(v*_-f*b+m*x)-n*(g*_-f*T+m*S)+i*(g*b-v*T+m*A)-r*(g*x-v*S+f*A)}determinantAffine(){let e=this.elements,t=e[0],n=e[4],i=e[8],r=e[1],a=e[5],o=e[9],c=e[2],l=e[6],h=e[10];return t*(a*h-o*l)-n*(r*h-o*c)+i*(r*l-a*c)}transpose(){let e=this.elements,t;return t=e[1],e[1]=e[4],e[4]=t,t=e[2],e[2]=e[8],e[8]=t,t=e[6],e[6]=e[9],e[9]=t,t=e[3],e[3]=e[12],e[12]=t,t=e[7],e[7]=e[13],e[13]=t,t=e[11],e[11]=e[14],e[14]=t,this}setPosition(e,t,n){let i=this.elements;return e.isVector3?(i[12]=e.x,i[13]=e.y,i[14]=e.z):(i[12]=e,i[13]=t,i[14]=n),this}invert(){let e=this.elements,t=e[0],n=e[1],i=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],h=e[8],u=e[9],d=e[10],p=e[11],g=e[12],v=e[13],f=e[14],m=e[15],_=t*o-n*a,b=t*c-i*a,x=t*l-r*a,T=n*c-i*o,S=n*l-r*o,A=i*l-r*c,y=h*v-u*g,E=h*f-d*g,I=h*m-p*g,L=u*f-d*v,F=u*m-p*v,V=d*m-p*f,D=_*V-b*F+x*L+T*I-S*E+A*y;if(D===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);let B=1/D;return e[0]=(o*V-c*F+l*L)*B,e[1]=(i*F-n*V-r*L)*B,e[2]=(v*A-f*S+m*T)*B,e[3]=(d*S-u*A-p*T)*B,e[4]=(c*I-a*V-l*E)*B,e[5]=(t*V-i*I+r*E)*B,e[6]=(f*x-g*A-m*b)*B,e[7]=(h*A-d*x+p*b)*B,e[8]=(a*F-o*I+l*y)*B,e[9]=(n*I-t*F-r*y)*B,e[10]=(g*S-v*x+m*_)*B,e[11]=(u*x-h*S-p*_)*B,e[12]=(o*E-a*L-c*y)*B,e[13]=(t*L-n*E+i*y)*B,e[14]=(v*b-g*T-f*_)*B,e[15]=(h*T-u*b+d*_)*B,this}scale(e){let t=this.elements,n=e.x,i=e.y,r=e.z;return t[0]*=n,t[4]*=i,t[8]*=r,t[1]*=n,t[5]*=i,t[9]*=r,t[2]*=n,t[6]*=i,t[10]*=r,t[3]*=n,t[7]*=i,t[11]*=r,this}getMaxScaleOnAxis(){let e=this.elements,t=e[0]*e[0]+e[1]*e[1]+e[2]*e[2],n=e[4]*e[4]+e[5]*e[5]+e[6]*e[6],i=e[8]*e[8]+e[9]*e[9]+e[10]*e[10];return Math.sqrt(Math.max(t,n,i))}makeTranslation(e,t,n){return e.isVector3?this.set(1,0,0,e.x,0,1,0,e.y,0,0,1,e.z,0,0,0,1):this.set(1,0,0,e,0,1,0,t,0,0,1,n,0,0,0,1),this}makeRotationX(e){let t=Math.cos(e),n=Math.sin(e);return this.set(1,0,0,0,0,t,-n,0,0,n,t,0,0,0,0,1),this}makeRotationY(e){let t=Math.cos(e),n=Math.sin(e);return this.set(t,0,n,0,0,1,0,0,-n,0,t,0,0,0,0,1),this}makeRotationZ(e){let t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,0,n,t,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(e,t){let n=Math.cos(t),i=Math.sin(t),r=1-n,a=e.x,o=e.y,c=e.z,l=r*a,h=r*o;return this.set(l*a+n,l*o-i*c,l*c+i*o,0,l*o+i*c,h*o+n,h*c-i*a,0,l*c-i*o,h*c+i*a,r*c*c+n,0,0,0,0,1),this}makeScale(e,t,n){return this.set(e,0,0,0,0,t,0,0,0,0,n,0,0,0,0,1),this}makeShear(e,t,n,i,r,a){return this.set(1,n,r,0,e,1,a,0,t,i,1,0,0,0,0,1),this}compose(e,t,n){let i=this.elements,r=t._x,a=t._y,o=t._z,c=t._w,l=r+r,h=a+a,u=o+o,d=r*l,p=r*h,g=r*u,v=a*h,f=a*u,m=o*u,_=c*l,b=c*h,x=c*u,T=n.x,S=n.y,A=n.z;return i[0]=(1-(v+m))*T,i[1]=(p+x)*T,i[2]=(g-b)*T,i[3]=0,i[4]=(p-x)*S,i[5]=(1-(d+m))*S,i[6]=(f+_)*S,i[7]=0,i[8]=(g+b)*A,i[9]=(f-_)*A,i[10]=(1-(d+v))*A,i[11]=0,i[12]=e.x,i[13]=e.y,i[14]=e.z,i[15]=1,this}decompose(e,t,n){let i=this.elements;e.x=i[12],e.y=i[13],e.z=i[14];let r=this.determinantAffine();if(r===0)return n.set(1,1,1),t.identity(),this;let a=Zs.set(i[0],i[1],i[2]).length(),o=Zs.set(i[4],i[5],i[6]).length(),c=Zs.set(i[8],i[9],i[10]).length();r<0&&(a=-a),$n.copy(this);let l=1/a,h=1/o,u=1/c;return $n.elements[0]*=l,$n.elements[1]*=l,$n.elements[2]*=l,$n.elements[4]*=h,$n.elements[5]*=h,$n.elements[6]*=h,$n.elements[8]*=u,$n.elements[9]*=u,$n.elements[10]*=u,t.setFromRotationMatrix($n),n.x=a,n.y=o,n.z=c,this}makePerspective(e,t,n,i,r,a,o=ni,c=!1){let l=this.elements,h=2*r/(t-e),u=2*r/(n-i),d=(t+e)/(t-e),p=(n+i)/(n-i),g,v;if(c)g=r/(a-r),v=a*r/(a-r);else if(o===ni)g=-(a+r)/(a-r),v=-2*a*r/(a-r);else if(o===gr)g=-a/(a-r),v=-a*r/(a-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+o);return l[0]=h,l[4]=0,l[8]=d,l[12]=0,l[1]=0,l[5]=u,l[9]=p,l[13]=0,l[2]=0,l[6]=0,l[10]=g,l[14]=v,l[3]=0,l[7]=0,l[11]=-1,l[15]=0,this}makeOrthographic(e,t,n,i,r,a,o=ni,c=!1){let l=this.elements,h=2/(t-e),u=2/(n-i),d=-(t+e)/(t-e),p=-(n+i)/(n-i),g,v;if(c)g=1/(a-r),v=a/(a-r);else if(o===ni)g=-2/(a-r),v=-(a+r)/(a-r);else if(o===gr)g=-1/(a-r),v=-r/(a-r);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+o);return l[0]=h,l[4]=0,l[8]=0,l[12]=d,l[1]=0,l[5]=u,l[9]=0,l[13]=p,l[2]=0,l[6]=0,l[10]=g,l[14]=v,l[3]=0,l[7]=0,l[11]=0,l[15]=1,this}equals(e){let t=this.elements,n=e.elements;for(let i=0;i<16;i++)if(t[i]!==n[i])return!1;return!0}fromArray(e,t=0){for(let n=0;n<16;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){let n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e[t+9]=n[9],e[t+10]=n[10],e[t+11]=n[11],e[t+12]=n[12],e[t+13]=n[13],e[t+14]=n[14],e[t+15]=n[15],e}},Zs=new R,$n=new je,eg=new R(0,0,0),tg=new R(1,1,1),ji=new R,ho=new R,wn=new R,Cd=new je,Rd=new nn,Oi=class s{constructor(e=0,t=0,n=0,i=s.DEFAULT_ORDER){this.isEuler=!0,this._x=e,this._y=t,this._z=n,this._order=i}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get order(){return this._order}set order(e){this._order=e,this._onChangeCallback()}set(e,t,n,i=this._order){return this._x=e,this._y=t,this._z=n,this._order=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(e){return this._x=e._x,this._y=e._y,this._z=e._z,this._order=e._order,this._onChangeCallback(),this}setFromRotationMatrix(e,t=this._order,n=!0){let i=e.elements,r=i[0],a=i[4],o=i[8],c=i[1],l=i[5],h=i[9],u=i[2],d=i[6],p=i[10];switch(t){case"XYZ":this._y=Math.asin(ot(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(-h,p),this._z=Math.atan2(-a,r)):(this._x=Math.atan2(d,l),this._z=0);break;case"YXZ":this._x=Math.asin(-ot(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(o,p),this._z=Math.atan2(c,l)):(this._y=Math.atan2(-u,r),this._z=0);break;case"ZXY":this._x=Math.asin(ot(d,-1,1)),Math.abs(d)<.9999999?(this._y=Math.atan2(-u,p),this._z=Math.atan2(-a,l)):(this._y=0,this._z=Math.atan2(c,r));break;case"ZYX":this._y=Math.asin(-ot(u,-1,1)),Math.abs(u)<.9999999?(this._x=Math.atan2(d,p),this._z=Math.atan2(c,r)):(this._x=0,this._z=Math.atan2(-a,l));break;case"YZX":this._z=Math.asin(ot(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(-h,l),this._y=Math.atan2(-u,r)):(this._x=0,this._y=Math.atan2(o,p));break;case"XZY":this._z=Math.asin(-ot(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(d,l),this._y=Math.atan2(o,r)):(this._x=Math.atan2(-h,p),this._y=0);break;default:Le("Euler: .setFromRotationMatrix() encountered an unknown order: "+t)}return this._order=t,n===!0&&this._onChangeCallback(),this}setFromQuaternion(e,t,n){return Cd.makeRotationFromQuaternion(e),this.setFromRotationMatrix(Cd,t,n)}setFromVector3(e,t=this._order){return this.set(e.x,e.y,e.z,t)}reorder(e){return Rd.setFromEuler(this),this.setFromQuaternion(Rd,e)}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._order===this._order}fromArray(e){return this._x=e[0],this._y=e[1],this._z=e[2],e[3]!==void 0&&(this._order=e[3]),this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._order,e}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}};Oi.DEFAULT_ORDER="XYZ";var ca=class{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}},ng=0,Id=new R,Js=new nn,Ii=new je,uo=new R,Xr=new R,ig=new R,sg=new nn,Pd=new R(1,0,0),Ld=new R(0,1,0),Nd=new R(0,0,1),Dd={type:"added"},rg={type:"removed"},$s={type:"childadded",child:null},jc={type:"childremoved",child:null},ft=class s extends vi{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:ng++}),this.uuid=kn(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=s.DEFAULT_UP.clone();let e=new R,t=new Oi,n=new nn,i=new R(1,1,1);function r(){n.setFromEuler(t,!1)}function a(){t.setFromQuaternion(n,void 0,!1)}t._onChange(r),n._onChange(a),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:e},rotation:{configurable:!0,enumerable:!0,value:t},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:i},modelViewMatrix:{value:new je},normalMatrix:{value:new Ze}}),this.matrix=new je,this.matrixWorld=new je,this.matrixAutoUpdate=s.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=s.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new ca,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.static=!1,this.userData={},this.pivot=null}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(e){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(e),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(e){return this.quaternion.premultiply(e),this}setRotationFromAxisAngle(e,t){this.quaternion.setFromAxisAngle(e,t)}setRotationFromEuler(e){this.quaternion.setFromEuler(e,!0)}setRotationFromMatrix(e){this.quaternion.setFromRotationMatrix(e)}setRotationFromQuaternion(e){this.quaternion.copy(e)}rotateOnAxis(e,t){return Js.setFromAxisAngle(e,t),this.quaternion.multiply(Js),this}rotateOnWorldAxis(e,t){return Js.setFromAxisAngle(e,t),this.quaternion.premultiply(Js),this}rotateX(e){return this.rotateOnAxis(Pd,e)}rotateY(e){return this.rotateOnAxis(Ld,e)}rotateZ(e){return this.rotateOnAxis(Nd,e)}translateOnAxis(e,t){return Id.copy(e).applyQuaternion(this.quaternion),this.position.add(Id.multiplyScalar(t)),this}translateX(e){return this.translateOnAxis(Pd,e)}translateY(e){return this.translateOnAxis(Ld,e)}translateZ(e){return this.translateOnAxis(Nd,e)}localToWorld(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(this.matrixWorld)}worldToLocal(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(Ii.copy(this.matrixWorld).invert())}lookAt(e,t,n){e.isVector3?uo.copy(e):uo.set(e,t,n);let i=this.parent;this.updateWorldMatrix(!0,!1),Xr.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?Ii.lookAt(Xr,uo,this.up):Ii.lookAt(uo,Xr,this.up),this.quaternion.setFromRotationMatrix(Ii),i&&(Ii.extractRotation(i.matrixWorld),Js.setFromRotationMatrix(Ii),this.quaternion.premultiply(Js.invert()))}add(e){if(arguments.length>1){for(let t=0;t<arguments.length;t++)this.add(arguments[t]);return this}return e===this?(He("Object3D.add: object can't be added as a child of itself.",e),this):(e&&e.isObject3D?(e.removeFromParent(),e.parent=this,this.children.push(e),e.dispatchEvent(Dd),$s.child=e,this.dispatchEvent($s),$s.child=null):He("Object3D.add: object not an instance of THREE.Object3D.",e),this)}remove(e){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}let t=this.children.indexOf(e);return t!==-1&&(e.parent=null,this.children.splice(t,1),e.dispatchEvent(rg),jc.child=e,this.dispatchEvent(jc),jc.child=null),this}removeFromParent(){let e=this.parent;return e!==null&&e.remove(this),this}clear(){return this.remove(...this.children)}attach(e){return this.updateWorldMatrix(!0,!1),Ii.copy(this.matrixWorld).invert(),e.parent!==null&&(e.parent.updateWorldMatrix(!0,!1),Ii.multiply(e.parent.matrixWorld)),e.applyMatrix4(Ii),e.removeFromParent(),e.parent=this,this.children.push(e),e.updateWorldMatrix(!1,!0),e.dispatchEvent(Dd),$s.child=e,this.dispatchEvent($s),$s.child=null,this}getObjectById(e){return this.getObjectByProperty("id",e)}getObjectByName(e){return this.getObjectByProperty("name",e)}getObjectByProperty(e,t){if(this[e]===t)return this;for(let n=0,i=this.children.length;n<i;n++){let a=this.children[n].getObjectByProperty(e,t);if(a!==void 0)return a}}getObjectsByProperty(e,t,n=[]){this[e]===t&&n.push(this);let i=this.children;for(let r=0,a=i.length;r<a;r++)i[r].getObjectsByProperty(e,t,n);return n}getWorldPosition(e){return this.updateWorldMatrix(!0,!1),e.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Xr,e,ig),e}getWorldScale(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Xr,sg,e),e}getWorldDirection(e){this.updateWorldMatrix(!0,!1);let t=this.matrixWorld.elements;return e.set(t[8],t[9],t[10]).normalize()}raycast(){}intersectsFrustum(){}traverse(e){e(this);let t=this.children;for(let n=0,i=t.length;n<i;n++)t[n].traverse(e)}traverseVisible(e){if(this.visible===!1)return;e(this);let t=this.children;for(let n=0,i=t.length;n<i;n++)t[n].traverseVisible(e)}traverseAncestors(e){let t=this.parent;t!==null&&(e(t),t.traverseAncestors(e))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale);let e=this.pivot;if(e!==null){let t=e.x,n=e.y,i=e.z,r=this.matrix.elements;r[12]+=t-r[0]*t-r[4]*n-r[8]*i,r[13]+=n-r[1]*t-r[5]*n-r[9]*i,r[14]+=i-r[2]*t-r[6]*n-r[10]*i}this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(e){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||e)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,e=!0);let t=this.children;for(let n=0,i=t.length;n<i;n++)t[n].updateMatrixWorld(e)}updateWorldMatrix(e,t,n=!1){let i=this.parent;if(e===!0&&i!==null&&i.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||n)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,n=!0),t===!0){let r=this.children;for(let a=0,o=r.length;a<o;a++)r[a].updateWorldMatrix(!1,!0,n)}}toJSON(e){let t=e===void 0||typeof e=="string",n={};t&&(e={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});let i={};i.uuid=this.uuid,i.type=this.type,i.name=this.name,i.castShadow=this.castShadow,i.receiveShadow=this.receiveShadow,i.visible=this.visible,i.frustumCulled=this.frustumCulled,i.renderOrder=this.renderOrder,i.static=this.static,i.matrixAutoUpdate=this.matrixAutoUpdate,Object.keys(this.userData).length>0&&(i.userData=this.userData),i.layers=this.layers.mask,i.matrix=this.matrix.toArray(),i.up=this.up.toArray(),this.pivot!==null&&(i.pivot=this.pivot.toArray()),this.morphTargetDictionary!==void 0&&(i.morphTargetDictionary=Object.assign({},this.morphTargetDictionary)),this.morphTargetInfluences!==void 0&&(i.morphTargetInfluences=this.morphTargetInfluences.slice()),this.isInstancedMesh&&(i.type="InstancedMesh",i.count=this.count,i.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(i.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(i.type="BatchedMesh",i.perObjectFrustumCulled=this.perObjectFrustumCulled,i.sortObjects=this.sortObjects,i.drawRanges=this._drawRanges,i.reservedRanges=this._reservedRanges,i.geometryInfo=this._geometryInfo.map(o=>({...o,boundingBox:o.boundingBox?o.boundingBox.toJSON():void 0,boundingSphere:o.boundingSphere?o.boundingSphere.toJSON():void 0})),i.instanceInfo=this._instanceInfo.map(o=>({...o})),i.availableInstanceIds=this._availableInstanceIds.slice(),i.availableGeometryIds=this._availableGeometryIds.slice(),i.nextIndexStart=this._nextIndexStart,i.nextVertexStart=this._nextVertexStart,i.geometryCount=this._geometryCount,i.maxInstanceCount=this._maxInstanceCount,i.maxVertexCount=this._maxVertexCount,i.maxIndexCount=this._maxIndexCount,i.geometryInitialized=this._geometryInitialized,i.matricesTexture=this._matricesTexture.toJSON(e),i.indirectTexture=this._indirectTexture.toJSON(e),this._colorsTexture!==null&&(i.colorsTexture=this._colorsTexture.toJSON(e)),this.boundingSphere!==null&&(i.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(i.boundingBox=this.boundingBox.toJSON()));function r(o,c){return o[c.uuid]===void 0&&(o[c.uuid]=c.toJSON(e)),c.uuid}if(this.isScene)this.background&&(this.background.isColor?i.background=this.background.toJSON():this.background.isTexture&&(i.background=this.background.toJSON(e).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(i.environment=this.environment.toJSON(e).uuid);else if(this.isMesh||this.isLine||this.isPoints){i.geometry=r(e.geometries,this.geometry);let o=this.geometry.parameters;if(o!==void 0&&o.shapes!==void 0){let c=o.shapes;if(Array.isArray(c))for(let l=0,h=c.length;l<h;l++){let u=c[l];r(e.shapes,u)}else r(e.shapes,c)}}if(this.isSkinnedMesh&&(i.bindMode=this.bindMode,i.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(e.skeletons,this.skeleton),i.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){let o=[];for(let c=0,l=this.material.length;c<l;c++)o.push(r(e.materials,this.material[c]));i.material=o}else i.material=r(e.materials,this.material);if(this.children.length>0){i.children=[];for(let o=0;o<this.children.length;o++)i.children.push(this.children[o].toJSON(e).object)}if(this.animations.length>0){i.animations=[];for(let o=0;o<this.animations.length;o++){let c=this.animations[o];i.animations.push(r(e.animations,c))}}if(t){let o=a(e.geometries),c=a(e.materials),l=a(e.textures),h=a(e.images),u=a(e.shapes),d=a(e.skeletons),p=a(e.animations),g=a(e.nodes);o.length>0&&(n.geometries=o),c.length>0&&(n.materials=c),l.length>0&&(n.textures=l),h.length>0&&(n.images=h),u.length>0&&(n.shapes=u),d.length>0&&(n.skeletons=d),p.length>0&&(n.animations=p),g.length>0&&(n.nodes=g)}return n.object=i,n;function a(o){let c=[];for(let l in o){let h=o[l];delete h.metadata,c.push(h)}return c}}clone(e){return new this.constructor().copy(this,e)}copy(e,t=!0){if(this.name=e.name,this.up.copy(e.up),this.position.copy(e.position),this.rotation.order=e.rotation.order,this.quaternion.copy(e.quaternion),this.scale.copy(e.scale),this.pivot=e.pivot!==null?e.pivot.clone():null,this.matrix.copy(e.matrix),this.matrixWorld.copy(e.matrixWorld),this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrixWorldAutoUpdate=e.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=e.matrixWorldNeedsUpdate,this.layers.mask=e.layers.mask,this.visible=e.visible,this.castShadow=e.castShadow,this.receiveShadow=e.receiveShadow,this.frustumCulled=e.frustumCulled,this.renderOrder=e.renderOrder,this.static=e.static,this.animations=e.animations.slice(),this.userData=JSON.parse(JSON.stringify(e.userData)),t===!0)for(let n=0;n<e.children.length;n++){let i=e.children[n];this.add(i.clone())}return this}dispose(){this.dispatchEvent({type:"dispose"})}};ft.DEFAULT_UP=new R(0,1,0);ft.DEFAULT_MATRIX_AUTO_UPDATE=!0;ft.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;var Ke=class extends ft{constructor(){super(),this.isGroup=!0,this.type="Group"}},ag={type:"move"},vr=class{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new Ke,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new Ke,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new R,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new R),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new Ke,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new R,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new R,this._grip.eventsEnabled=!1),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){let t=this._hand;if(t)for(let n of e.hand.values())this._getHandJoint(t,n)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,t,n){let i=null,r=null,a=null,o=this._targetRay,c=this._grip,l=this._hand;if(e&&t.session.visibilityState!=="visible-blurred"){if(l&&e.hand){a=!0;for(let v of e.hand.values()){let f=t.getJointPose(v,n),m=this._getHandJoint(l,v);f!==null&&(m.matrix.fromArray(f.transform.matrix),m.matrix.decompose(m.position,m.rotation,m.scale),m.matrixWorldNeedsUpdate=!0,m.jointRadius=f.radius),m.visible=f!==null}let h=l.joints["index-finger-tip"],u=l.joints["thumb-tip"],d=h.position.distanceTo(u.position),p=.02,g=.005;l.inputState.pinching&&d>p+g?(l.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!l.inputState.pinching&&d<=p-g&&(l.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else c!==null&&e.gripSpace&&(r=t.getPose(e.gripSpace,n),r!==null&&(c.matrix.fromArray(r.transform.matrix),c.matrix.decompose(c.position,c.rotation,c.scale),c.matrixWorldNeedsUpdate=!0,r.linearVelocity?(c.hasLinearVelocity=!0,c.linearVelocity.copy(r.linearVelocity)):c.hasLinearVelocity=!1,r.angularVelocity?(c.hasAngularVelocity=!0,c.angularVelocity.copy(r.angularVelocity)):c.hasAngularVelocity=!1,c.eventsEnabled&&c.dispatchEvent({type:"gripUpdated",data:e,target:this})));o!==null&&(i=t.getPose(e.targetRaySpace,n),i===null&&r!==null&&(i=r),i!==null&&(o.matrix.fromArray(i.transform.matrix),o.matrix.decompose(o.position,o.rotation,o.scale),o.matrixWorldNeedsUpdate=!0,i.linearVelocity?(o.hasLinearVelocity=!0,o.linearVelocity.copy(i.linearVelocity)):o.hasLinearVelocity=!1,i.angularVelocity?(o.hasAngularVelocity=!0,o.angularVelocity.copy(i.angularVelocity)):o.hasAngularVelocity=!1,this.dispatchEvent(ag)))}return o!==null&&(o.visible=i!==null),c!==null&&(c.visible=r!==null),l!==null&&(l.visible=a!==null),this}_getHandJoint(e,t){if(e.joints[t.jointName]===void 0){let n=new Ke;n.matrixAutoUpdate=!1,n.visible=!1,e.joints[t.jointName]=n,e.add(n)}return e.joints[t.jointName]}},Qf={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Qi={h:0,s:0,l:0},fo={h:0,s:0,l:0};function Qc(s,e,t){return t<0&&(t+=1),t>1&&(t-=1),t<1/6?s+(e-s)*6*t:t<1/2?e:t<2/3?s+(e-s)*6*(2/3-t):s}var Me=class{constructor(e,t,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,t,n)}set(e,t,n){if(t===void 0&&n===void 0){let i=e;i&&i.isColor?this.copy(i):typeof i=="number"?this.setHex(i):typeof i=="string"&&this.setStyle(i)}else this.setRGB(e,t,n);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,t=Ct){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,it.colorSpaceToWorking(this,t),this}setRGB(e,t,n,i=it.workingColorSpace){return this.r=e,this.g=t,this.b=n,it.colorSpaceToWorking(this,i),this}setHSL(e,t,n,i=it.workingColorSpace){if(e=tu(e,1),t=ot(t,0,1),n=ot(n,0,1),t===0)this.r=this.g=this.b=n;else{let r=n<=.5?n*(1+t):n+t-n*t,a=2*n-r;this.r=Qc(a,r,e+1/3),this.g=Qc(a,r,e),this.b=Qc(a,r,e-1/3)}return it.colorSpaceToWorking(this,i),this}setStyle(e,t=Ct){function n(r){r!==void 0&&parseFloat(r)<1&&Le("Color: Alpha component of "+e+" will be ignored.")}let i;if(i=/^(\w+)\(([^\)]*)\)/.exec(e)){let r,a=i[1],o=i[2];switch(a){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,t);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,t);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,t);break;default:Le("Color: Unknown color model "+e)}}else if(i=/^\#([A-Fa-f\d]+)$/.exec(e)){let r=i[1],a=r.length;if(a===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,t);if(a===6)return this.setHex(parseInt(r,16),t);Le("Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,t);return this}setColorName(e,t=Ct){let n=Qf[e.toLowerCase()];return n!==void 0?this.setHex(n,t):Le("Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=Fi(e.r),this.g=Fi(e.g),this.b=Fi(e.b),this}copyLinearToSRGB(e){return this.r=fr(e.r),this.g=fr(e.g),this.b=fr(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=Ct){return it.workingToColorSpace(hn.copy(this),e),Math.round(ot(hn.r*255,0,255))*65536+Math.round(ot(hn.g*255,0,255))*256+Math.round(ot(hn.b*255,0,255))}getHexString(e=Ct){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,t=it.workingColorSpace){it.workingToColorSpace(hn.copy(this),t);let n=hn.r,i=hn.g,r=hn.b,a=Math.max(n,i,r),o=Math.min(n,i,r),c,l,h=(o+a)/2;if(o===a)c=0,l=0;else{let u=a-o;switch(l=h<=.5?u/(a+o):u/(2-a-o),a){case n:c=(i-r)/u+(i<r?6:0);break;case i:c=(r-n)/u+2;break;case r:c=(n-i)/u+4;break}c/=6}return e.h=c,e.s=l,e.l=h,e}getRGB(e,t=it.workingColorSpace){return it.workingToColorSpace(hn.copy(this),t),e.r=hn.r,e.g=hn.g,e.b=hn.b,e}getStyle(e=Ct){it.workingToColorSpace(hn.copy(this),e);let t=hn.r,n=hn.g,i=hn.b;return e!==Ct?`color(${e} ${t.toFixed(3)} ${n.toFixed(3)} ${i.toFixed(3)})`:`rgb(${Math.round(t*255)},${Math.round(n*255)},${Math.round(i*255)})`}offsetHSL(e,t,n){return this.getHSL(Qi),this.setHSL(Qi.h+e,Qi.s+t,Qi.l+n)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,t){return this.r=e.r+t.r,this.g=e.g+t.g,this.b=e.b+t.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,t){return this.r+=(e.r-this.r)*t,this.g+=(e.g-this.g)*t,this.b+=(e.b-this.b)*t,this}lerpColors(e,t,n){return this.r=e.r+(t.r-e.r)*n,this.g=e.g+(t.g-e.g)*n,this.b=e.b+(t.b-e.b)*n,this}lerpHSL(e,t){this.getHSL(Qi),e.getHSL(fo);let n=ia(Qi.h,fo.h,t),i=ia(Qi.s,fo.s,t),r=ia(Qi.l,fo.l,t);return this.setHSL(n,i,r),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){let t=this.r,n=this.g,i=this.b,r=e.elements;return this.r=r[0]*t+r[3]*n+r[6]*i,this.g=r[1]*t+r[4]*n+r[7]*i,this.b=r[2]*t+r[5]*n+r[8]*i,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,t=0){return this.r=e[t],this.g=e[t+1],this.b=e[t+2],this}toArray(e=[],t=0){return e[t]=this.r,e[t+1]=this.g,e[t+2]=this.b,e}fromBufferAttribute(e,t){return this.r=e.getX(t),this.g=e.getY(t),this.b=e.getZ(t),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}},hn=new Me;Me.NAMES=Qf;var ha=class s{constructor(e,t=25e-5){this.isFogExp2=!0,this.name="",this.color=new Me(e),this.density=t}clone(){return new s(this.color,this.density)}toJSON(){return{type:"FogExp2",name:this.name,color:this.color.getHex(),density:this.density}}},ua=class s{constructor(e,t=1,n=1e3){this.isFog=!0,this.name="",this.color=new Me(e),this.near=t,this.far=n}clone(){return new s(this.color,this.near,this.far)}toJSON(){return{type:"Fog",name:this.name,color:this.color.getHex(),near:this.near,far:this.far}}},ss=class extends ft{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new Oi,this.environmentIntensity=1,this.environmentRotation=new Oi,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,t){return super.copy(e,t),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,this.backgroundRotation.copy(e.backgroundRotation),this.environmentIntensity=e.environmentIntensity,this.environmentRotation.copy(e.environmentRotation),e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){let t=super.toJSON(e);return this.fog!==null&&(t.object.fog=this.fog.toJSON()),t.object.backgroundBlurriness=this.backgroundBlurriness,t.object.backgroundIntensity=this.backgroundIntensity,t.object.backgroundRotation=this.backgroundRotation.toArray(),t.object.environmentIntensity=this.environmentIntensity,t.object.environmentRotation=this.environmentRotation.toArray(),t}},jn=new R,Pi=new R,eh=new R,Li=new R,js=new R,Qs=new R,Ud=new R,th=new R,nh=new R,ih=new R,sh=new At,rh=new At,ah=new At,mi=class s{constructor(e=new R,t=new R,n=new R){this.a=e,this.b=t,this.c=n}static getNormal(e,t,n,i){i.subVectors(n,t),jn.subVectors(e,t),i.cross(jn);let r=i.lengthSq();return r>0?i.multiplyScalar(1/Math.sqrt(r)):i.set(0,0,0)}static getBarycoord(e,t,n,i,r){jn.subVectors(i,t),Pi.subVectors(n,t),eh.subVectors(e,t);let a=jn.dot(jn),o=jn.dot(Pi),c=jn.dot(eh),l=Pi.dot(Pi),h=Pi.dot(eh),u=a*l-o*o;if(u===0)return r.set(0,0,0),null;let d=1/u,p=(l*c-o*h)*d,g=(a*h-o*c)*d;return r.set(1-p-g,g,p)}static containsPoint(e,t,n,i){return this.getBarycoord(e,t,n,i,Li)===null?!1:Li.x>=0&&Li.y>=0&&Li.x+Li.y<=1}static getInterpolation(e,t,n,i,r,a,o,c){return this.getBarycoord(e,t,n,i,Li)===null?(c.x=0,c.y=0,"z"in c&&(c.z=0),"w"in c&&(c.w=0),null):(c.setScalar(0),c.addScaledVector(r,Li.x),c.addScaledVector(a,Li.y),c.addScaledVector(o,Li.z),c)}static getInterpolatedAttribute(e,t,n,i,r,a){return sh.setScalar(0),rh.setScalar(0),ah.setScalar(0),sh.fromBufferAttribute(e,t),rh.fromBufferAttribute(e,n),ah.fromBufferAttribute(e,i),a.setScalar(0),a.addScaledVector(sh,r.x),a.addScaledVector(rh,r.y),a.addScaledVector(ah,r.z),a}static isFrontFacing(e,t,n,i){return jn.subVectors(n,t),Pi.subVectors(e,t),jn.cross(Pi).dot(i)<0}set(e,t,n){return this.a.copy(e),this.b.copy(t),this.c.copy(n),this}setFromPointsAndIndices(e,t,n,i){return this.a.copy(e[t]),this.b.copy(e[n]),this.c.copy(e[i]),this}setFromAttributeAndIndices(e,t,n,i){return this.a.fromBufferAttribute(e,t),this.b.fromBufferAttribute(e,n),this.c.fromBufferAttribute(e,i),this}clone(){return new this.constructor().copy(this)}copy(e){return this.a.copy(e.a),this.b.copy(e.b),this.c.copy(e.c),this}getArea(){return jn.subVectors(this.c,this.b),Pi.subVectors(this.a,this.b),jn.cross(Pi).length()*.5}getMidpoint(e){return e.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(e){return s.getNormal(this.a,this.b,this.c,e)}getPlane(e){return e.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(e,t){return s.getBarycoord(e,this.a,this.b,this.c,t)}getInterpolation(e,t,n,i,r){return s.getInterpolation(e,this.a,this.b,this.c,t,n,i,r)}containsPoint(e){return s.containsPoint(e,this.a,this.b,this.c)}isFrontFacing(e){return s.isFrontFacing(this.a,this.b,this.c,e)}intersectsBox(e){return e.intersectsTriangle(this)}closestPointToPoint(e,t){let n=this.a,i=this.b,r=this.c,a,o;js.subVectors(i,n),Qs.subVectors(r,n),th.subVectors(e,n);let c=js.dot(th),l=Qs.dot(th);if(c<=0&&l<=0)return t.copy(n);nh.subVectors(e,i);let h=js.dot(nh),u=Qs.dot(nh);if(h>=0&&u<=h)return t.copy(i);let d=c*u-h*l;if(d<=0&&c>=0&&h<=0)return a=c/(c-h),t.copy(n).addScaledVector(js,a);ih.subVectors(e,r);let p=js.dot(ih),g=Qs.dot(ih);if(g>=0&&p<=g)return t.copy(r);let v=p*l-c*g;if(v<=0&&l>=0&&g<=0)return o=l/(l-g),t.copy(n).addScaledVector(Qs,o);let f=h*g-p*u;if(f<=0&&u-h>=0&&p-g>=0)return Ud.subVectors(r,i),o=(u-h)/(u-h+(p-g)),t.copy(i).addScaledVector(Ud,o);let m=1/(f+v+d);return a=v*m,o=d*m,t.copy(n).addScaledVector(js,a).addScaledVector(Qs,o)}equals(e){return e.a.equals(this.a)&&e.b.equals(this.b)&&e.c.equals(this.c)}},En=class{constructor(e=new R(1/0,1/0,1/0),t=new R(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=t}set(e,t){return this.min.copy(e),this.max.copy(t),this}setFromArray(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t+=3)this.expandByPoint(Qn.fromArray(e,t));return this}setFromBufferAttribute(e){this.makeEmpty();for(let t=0,n=e.count;t<n;t++)this.expandByPoint(Qn.fromBufferAttribute(e,t));return this}setFromPoints(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t++)this.expandByPoint(e[t]);return this}setFromCenterAndSize(e,t){let n=Qn.copy(t).multiplyScalar(.5);return this.min.copy(e).sub(n),this.max.copy(e).add(n),this}setFromObject(e,t=!1){return this.makeEmpty(),this.expandByObject(e,t)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,t=!1){e.updateWorldMatrix(!1,!1);let n=e.geometry;if(n!==void 0){let r=n.getAttribute("position");if(t===!0&&r!==void 0&&e.isInstancedMesh!==!0)for(let a=0,o=r.count;a<o;a++)e.isMesh===!0?e.getVertexPosition(a,Qn):Qn.fromBufferAttribute(r,a),Qn.applyMatrix4(e.matrixWorld),this.expandByPoint(Qn);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),po.copy(e.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),po.copy(n.boundingBox)),po.applyMatrix4(e.matrixWorld),this.union(po)}let i=e.children;for(let r=0,a=i.length;r<a;r++)this.expandByObject(i[r],t);return this}containsPoint(e){return e.x>=this.min.x&&e.x<=this.max.x&&e.y>=this.min.y&&e.y<=this.max.y&&e.z>=this.min.z&&e.z<=this.max.z}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,t){return t.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return e.max.x>=this.min.x&&e.min.x<=this.max.x&&e.max.y>=this.min.y&&e.min.y<=this.max.y&&e.max.z>=this.min.z&&e.min.z<=this.max.z}intersectsSphere(e){return this.clampPoint(e.center,Qn),Qn.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let t,n;return e.normal.x>0?(t=e.normal.x*this.min.x,n=e.normal.x*this.max.x):(t=e.normal.x*this.max.x,n=e.normal.x*this.min.x),e.normal.y>0?(t+=e.normal.y*this.min.y,n+=e.normal.y*this.max.y):(t+=e.normal.y*this.max.y,n+=e.normal.y*this.min.y),e.normal.z>0?(t+=e.normal.z*this.min.z,n+=e.normal.z*this.max.z):(t+=e.normal.z*this.max.z,n+=e.normal.z*this.min.z),t<=-e.constant&&n>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(qr),mo.subVectors(this.max,qr),er.subVectors(e.a,qr),tr.subVectors(e.b,qr),nr.subVectors(e.c,qr),es.subVectors(tr,er),ts.subVectors(nr,tr),ys.subVectors(er,nr);let t=[0,-es.z,es.y,0,-ts.z,ts.y,0,-ys.z,ys.y,es.z,0,-es.x,ts.z,0,-ts.x,ys.z,0,-ys.x,-es.y,es.x,0,-ts.y,ts.x,0,-ys.y,ys.x,0];return!oh(t,er,tr,nr,mo)||(t=[1,0,0,0,1,0,0,0,1],!oh(t,er,tr,nr,mo))?!1:(go.crossVectors(es,ts),t=[go.x,go.y,go.z],oh(t,er,tr,nr,mo))}clampPoint(e,t){return t.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,Qn).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(Qn).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(Ni[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),Ni[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),Ni[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),Ni[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),Ni[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),Ni[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),Ni[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),Ni[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(Ni),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(e){return this.min.fromArray(e.min),this.max.fromArray(e.max),this}},Ni=[new R,new R,new R,new R,new R,new R,new R,new R],Qn=new R,po=new En,er=new R,tr=new R,nr=new R,es=new R,ts=new R,ys=new R,qr=new R,mo=new R,go=new R,vs=new R;function oh(s,e,t,n,i){for(let r=0,a=s.length-3;r<=a;r+=3){vs.fromArray(s,r);let o=i.x*Math.abs(vs.x)+i.y*Math.abs(vs.y)+i.z*Math.abs(vs.z),c=e.dot(vs),l=t.dot(vs),h=n.dot(vs);if(Math.max(-Math.max(c,l,h),Math.min(c,l,h))>o)return!1}return!0}var Zt=new R,xo=new ne,og=0,Ft=class extends vi{constructor(e,t,n=!1){if(super(),Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:og++}),this.name="",this.array=e,this.itemSize=t,this.count=e!==void 0?e.length/t:0,this.normalized=n,this.usage=jh,this.updateRanges=[],this.gpuType=Dn,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,t,n){e*=this.itemSize,n*=t.itemSize;for(let i=0,r=this.itemSize;i<r;i++)this.array[e+i]=t.array[n+i];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let t=0,n=this.count;t<n;t++)xo.fromBufferAttribute(this,t),xo.applyMatrix3(e),this.setXY(t,xo.x,xo.y);else if(this.itemSize===3)for(let t=0,n=this.count;t<n;t++)Zt.fromBufferAttribute(this,t),Zt.applyMatrix3(e),this.setXYZ(t,Zt.x,Zt.y,Zt.z);return this}applyMatrix4(e){for(let t=0,n=this.count;t<n;t++)Zt.fromBufferAttribute(this,t),Zt.applyMatrix4(e),this.setXYZ(t,Zt.x,Zt.y,Zt.z);return this}applyNormalMatrix(e){for(let t=0,n=this.count;t<n;t++)Zt.fromBufferAttribute(this,t),Zt.applyNormalMatrix(e),this.setXYZ(t,Zt.x,Zt.y,Zt.z);return this}transformDirection(e){for(let t=0,n=this.count;t<n;t++)Zt.fromBufferAttribute(this,t),Zt.transformDirection(e),this.setXYZ(t,Zt.x,Zt.y,Zt.z);return this}set(e,t=0){return this.array.set(e,t),this}getComponent(e,t){let n=this.array[e*this.itemSize+t];return this.normalized&&(n=ti(n,this.array)),n}setComponent(e,t,n){return this.normalized&&(n=wt(n,this.array)),this.array[e*this.itemSize+t]=n,this}getX(e){let t=this.array[e*this.itemSize];return this.normalized&&(t=ti(t,this.array)),t}setX(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize]=t,this}getY(e){let t=this.array[e*this.itemSize+1];return this.normalized&&(t=ti(t,this.array)),t}setY(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize+1]=t,this}getZ(e){let t=this.array[e*this.itemSize+2];return this.normalized&&(t=ti(t,this.array)),t}setZ(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize+2]=t,this}getW(e){let t=this.array[e*this.itemSize+3];return this.normalized&&(t=ti(t,this.array)),t}setW(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize+3]=t,this}setXY(e,t,n){return e*=this.itemSize,this.normalized&&(t=wt(t,this.array),n=wt(n,this.array)),this.array[e+0]=t,this.array[e+1]=n,this}setXYZ(e,t,n,i){return e*=this.itemSize,this.normalized&&(t=wt(t,this.array),n=wt(n,this.array),i=wt(i,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=i,this}setXYZW(e,t,n,i,r){return e*=this.itemSize,this.normalized&&(t=wt(t,this.array),n=wt(n,this.array),i=wt(i,this.array),r=wt(r,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=i,this.array[e+3]=r,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){let e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return e.name=this.name,e.usage=this.usage,e.gpuType=this.gpuType,e}dispose(){this.dispatchEvent({type:"dispose"})}};var Es=class extends Ft{constructor(e,t,n){super(new Uint16Array(e),t,n)}};var da=class extends Ft{constructor(e,t,n){super(new Uint32Array(e),t,n)}};var Oe=class extends Ft{constructor(e,t,n){super(new Float32Array(e),t,n)}},lg=new En,Yr=new R,lh=new R,yn=class{constructor(e=new R,t=-1){this.isSphere=!0,this.center=e,this.radius=t}set(e,t){return this.center.copy(e),this.radius=t,this}setFromPoints(e,t){let n=this.center;t!==void 0?n.copy(t):lg.setFromPoints(e).getCenter(n);let i=0;for(let r=0,a=e.length;r<a;r++)i=Math.max(i,n.distanceToSquared(e[r]));return this.radius=Math.sqrt(i),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){let t=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=t*t}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,t){let n=this.center.distanceToSquared(e);return t.copy(e),n>this.radius*this.radius&&(t.sub(this.center).normalize(),t.multiplyScalar(this.radius).add(this.center)),t}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;Yr.subVectors(e,this.center);let t=Yr.lengthSq();if(t>this.radius*this.radius){let n=Math.sqrt(t),i=(n-this.radius)*.5;this.center.addScaledVector(Yr,i/n),this.radius+=i}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(lh.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(Yr.copy(e.center).add(lh)),this.expandByPoint(Yr.copy(e.center).sub(lh))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(e){return this.radius=e.radius,this.center.fromArray(e.center),this}},cg=0,Bn=new je,ch=new ft,ir=new R,An=new En,Kr=new En,tn=new R,tt=class s extends vi{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:cg++}),this.uuid=kn(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.indirectOffset=0,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={},this._transformed=!1}getIndex(){return this.index}setIndex(e){return Array.isArray(e)?this.index=new(Nm(e)?da:Es)(e,1):this.index=e,this}setIndirect(e,t=0){return this.indirect=e,this.indirectOffset=t,this}getIndirect(){return this.indirect}getAttribute(e){return this.attributes[e]}setAttribute(e,t){return this.attributes[e]=t,this}deleteAttribute(e){return delete this.attributes[e],this}hasAttribute(e){return this.attributes[e]!==void 0}addGroup(e,t,n=0){this.groups.push({start:e,count:t,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(e,t){this.drawRange.start=e,this.drawRange.count=t}applyMatrix4(e){let t=this.attributes.position;t!==void 0&&(t.applyMatrix4(e),t.needsUpdate=!0);let n=this.attributes.normal;if(n!==void 0){let r=new Ze().getNormalMatrix(e);n.applyNormalMatrix(r),n.needsUpdate=!0}let i=this.attributes.tangent;return i!==void 0&&(i.transformDirection(e),i.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this._transformed=!0,this}applyQuaternion(e){return Bn.makeRotationFromQuaternion(e),this.applyMatrix4(Bn),this}rotateX(e){return Bn.makeRotationX(e),this.applyMatrix4(Bn),this}rotateY(e){return Bn.makeRotationY(e),this.applyMatrix4(Bn),this}rotateZ(e){return Bn.makeRotationZ(e),this.applyMatrix4(Bn),this}translate(e,t,n){return Bn.makeTranslation(e,t,n),this.applyMatrix4(Bn),this}scale(e,t,n){return Bn.makeScale(e,t,n),this.applyMatrix4(Bn),this}lookAt(e){return ch.lookAt(e),ch.updateMatrix(),this.applyMatrix4(ch.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(ir).negate(),this.translate(ir.x,ir.y,ir.z),this}setFromPoints(e){let t=this.getAttribute("position");if(t===void 0){let n=[];for(let i=0,r=e.length;i<r;i++){let a=e[i];n.push(a.x,a.y,a.z||0)}this.setAttribute("position",new Oe(n,3))}else{let n=Math.min(e.length,t.count);for(let i=0;i<n;i++){let r=e[i];t.setXYZ(i,r.x,r.y,r.z||0)}e.length>t.count&&Le("BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),t.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new En);let e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){He("BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new R(-1/0,-1/0,-1/0),new R(1/0,1/0,1/0));return}if(e!==void 0){if(this.boundingBox.setFromBufferAttribute(e),t)for(let n=0,i=t.length;n<i;n++){let r=t[n];An.setFromBufferAttribute(r),this.morphTargetsRelative?(tn.addVectors(this.boundingBox.min,An.min),this.boundingBox.expandByPoint(tn),tn.addVectors(this.boundingBox.max,An.max),this.boundingBox.expandByPoint(tn)):(this.boundingBox.expandByPoint(An.min),this.boundingBox.expandByPoint(An.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&He('BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new yn);let e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){He("BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new R,1/0);return}if(e){let n=this.boundingSphere.center;if(An.setFromBufferAttribute(e),t)for(let r=0,a=t.length;r<a;r++){let o=t[r];Kr.setFromBufferAttribute(o),this.morphTargetsRelative?(tn.addVectors(An.min,Kr.min),An.expandByPoint(tn),tn.addVectors(An.max,Kr.max),An.expandByPoint(tn)):(An.expandByPoint(Kr.min),An.expandByPoint(Kr.max))}An.getCenter(n);let i=0;for(let r=0,a=e.count;r<a;r++)tn.fromBufferAttribute(e,r),i=Math.max(i,n.distanceToSquared(tn));if(t)for(let r=0,a=t.length;r<a;r++){let o=t[r],c=this.morphTargetsRelative;for(let l=0,h=o.count;l<h;l++)tn.fromBufferAttribute(o,l),c&&(ir.fromBufferAttribute(e,l),tn.add(ir)),i=Math.max(i,n.distanceToSquared(tn))}this.boundingSphere.radius=Math.sqrt(i),isNaN(this.boundingSphere.radius)&&He('BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){let e=this.index,t=this.attributes;if(e===null||t.position===void 0||t.normal===void 0||t.uv===void 0){He("BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}let n=t.position,i=t.normal,r=t.uv,a=this.getAttribute("tangent");(a===void 0||a.count!==n.count)&&(a=new Ft(new Float32Array(4*n.count),4),this.setAttribute("tangent",a));let o=[],c=[];for(let y=0;y<n.count;y++)o[y]=new R,c[y]=new R;let l=new R,h=new R,u=new R,d=new ne,p=new ne,g=new ne,v=new R,f=new R;function m(y,E,I){l.fromBufferAttribute(n,y),h.fromBufferAttribute(n,E),u.fromBufferAttribute(n,I),d.fromBufferAttribute(r,y),p.fromBufferAttribute(r,E),g.fromBufferAttribute(r,I),h.sub(l),u.sub(l),p.sub(d),g.sub(d);let L=1/(p.x*g.y-g.x*p.y);isFinite(L)&&(v.copy(h).multiplyScalar(g.y).addScaledVector(u,-p.y).multiplyScalar(L),f.copy(u).multiplyScalar(p.x).addScaledVector(h,-g.x).multiplyScalar(L),o[y].add(v),o[E].add(v),o[I].add(v),c[y].add(f),c[E].add(f),c[I].add(f))}let _=this.groups;_.length===0&&(_=[{start:0,count:e.count}]);for(let y=0,E=_.length;y<E;++y){let I=_[y],L=I.start,F=I.count;for(let V=L,D=L+F;V<D;V+=3)m(e.getX(V+0),e.getX(V+1),e.getX(V+2))}let b=new R,x=new R,T=new R,S=new R;function A(y){T.fromBufferAttribute(i,y),S.copy(T);let E=o[y];b.copy(E),b.sub(T.multiplyScalar(T.dot(E))).normalize(),x.crossVectors(S,E);let L=x.dot(c[y])<0?-1:1;a.setXYZW(y,b.x,b.y,b.z,L)}for(let y=0,E=_.length;y<E;++y){let I=_[y],L=I.start,F=I.count;for(let V=L,D=L+F;V<D;V+=3)A(e.getX(V+0)),A(e.getX(V+1)),A(e.getX(V+2))}this._transformed=!0}computeVertexNormals(){let e=this.index,t=this.getAttribute("position");if(t!==void 0){let n=this.getAttribute("normal");if(n===void 0||n.count!==t.count)n=new Ft(new Float32Array(t.count*3),3),this.setAttribute("normal",n);else for(let d=0,p=n.count;d<p;d++)n.setXYZ(d,0,0,0);let i=new R,r=new R,a=new R,o=new R,c=new R,l=new R,h=new R,u=new R;if(e)for(let d=0,p=e.count;d<p;d+=3){let g=e.getX(d+0),v=e.getX(d+1),f=e.getX(d+2);i.fromBufferAttribute(t,g),r.fromBufferAttribute(t,v),a.fromBufferAttribute(t,f),h.subVectors(a,r),u.subVectors(i,r),h.cross(u),o.fromBufferAttribute(n,g),c.fromBufferAttribute(n,v),l.fromBufferAttribute(n,f),o.add(h),c.add(h),l.add(h),n.setXYZ(g,o.x,o.y,o.z),n.setXYZ(v,c.x,c.y,c.z),n.setXYZ(f,l.x,l.y,l.z)}else for(let d=0,p=t.count;d<p;d+=3)i.fromBufferAttribute(t,d+0),r.fromBufferAttribute(t,d+1),a.fromBufferAttribute(t,d+2),h.subVectors(a,r),u.subVectors(i,r),h.cross(u),n.setXYZ(d+0,h.x,h.y,h.z),n.setXYZ(d+1,h.x,h.y,h.z),n.setXYZ(d+2,h.x,h.y,h.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){let e=this.attributes.normal;for(let t=0,n=e.count;t<n;t++)tn.fromBufferAttribute(e,t),tn.normalize(),e.setXYZ(t,tn.x,tn.y,tn.z)}toNonIndexed(){function e(o,c){let l=o.array,h=o.itemSize,u=o.normalized,d=new l.constructor(c.length*h),p=0,g=0;for(let v=0,f=c.length;v<f;v++){o.isInterleavedBufferAttribute?p=c[v]*o.data.stride+o.offset:p=c[v]*h;for(let m=0;m<h;m++)d[g++]=l[p++]}return new Ft(d,h,u)}if(this.index===null)return Le("BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;let t=new s,n=this.index.array,i=this.attributes;for(let o in i){let c=i[o],l=e(c,n);t.setAttribute(o,l)}let r=this.morphAttributes;for(let o in r){let c=[],l=r[o];for(let h=0,u=l.length;h<u;h++){let d=l[h],p=e(d,n);c.push(p)}t.morphAttributes[o]=c}t.morphTargetsRelative=this.morphTargetsRelative;let a=this.groups;for(let o=0,c=a.length;o<c;o++){let l=a[o];t.addGroup(l.start,l.count,l.materialIndex)}return t}toJSON(){let e={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(e.uuid=this.uuid,e.type=this.parameters!==void 0&&this._transformed===!0?"BufferGeometry":this.type,e.name=this.name,Object.keys(this.userData).length>0&&(e.userData=this.userData),this.parameters!==void 0&&this._transformed!==!0){let c=this.parameters;for(let l in c)c[l]!==void 0&&(e[l]=c[l]);return e}e.data={attributes:{}};let t=this.index;t!==null&&(e.data.index={type:t.array.constructor.name,array:Array.prototype.slice.call(t.array)});let n=this.attributes;for(let c in n){let l=n[c];e.data.attributes[c]=l.toJSON(e.data)}let i={},r=!1;for(let c in this.morphAttributes){let l=this.morphAttributes[c],h=[];for(let u=0,d=l.length;u<d;u++){let p=l[u];h.push(p.toJSON(e.data))}h.length>0&&(i[c]=h,r=!0)}r&&(e.data.morphAttributes=i,e.data.morphTargetsRelative=this.morphTargetsRelative);let a=this.groups;a.length>0&&(e.data.groups=JSON.parse(JSON.stringify(a)));let o=this.boundingSphere;return o!==null&&(e.data.boundingSphere=o.toJSON()),e}clone(){return new this.constructor().copy(this)}copy(e){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;let t={};this.name=e.name;let n=e.index;n!==null&&this.setIndex(n.clone());let i=e.attributes;for(let l in i){let h=i[l];this.setAttribute(l,h.clone(t))}let r=e.morphAttributes;for(let l in r){let h=[],u=r[l];for(let d=0,p=u.length;d<p;d++)h.push(u[d].clone(t));this.morphAttributes[l]=h}this.morphTargetsRelative=e.morphTargetsRelative;let a=e.groups;for(let l=0,h=a.length;l<h;l++){let u=a[l];this.addGroup(u.start,u.count,u.materialIndex)}let o=e.boundingBox;o!==null&&(this.boundingBox=o.clone());let c=e.boundingSphere;return c!==null&&(this.boundingSphere=c.clone()),this.drawRange.start=e.drawRange.start,this.drawRange.count=e.drawRange.count,this.userData=e.userData,this._transformed=e._transformed,this}dispose(){this.dispatchEvent({type:"dispose"})}},Cs=class{constructor(e,t){this.isInterleavedBuffer=!0,this.array=e,this.stride=t,this.count=e!==void 0?e.length/t:0,this.usage=jh,this.updateRanges=[],this.version=0,this.uuid=kn()}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.array=new e.array.constructor(e.array),this.count=e.count,this.stride=e.stride,this.usage=e.usage,this}copyAt(e,t,n){e*=this.stride,n*=t.stride;for(let i=0,r=this.stride;i<r;i++)this.array[e+i]=t.array[n+i];return this}set(e,t=0){return this.array.set(e,t),this}clone(e){e.arrayBuffers===void 0&&(e.arrayBuffers={}),this.array.buffer._uuid===void 0&&(this.array.buffer._uuid=kn()),e.arrayBuffers[this.array.buffer._uuid]===void 0&&(e.arrayBuffers[this.array.buffer._uuid]=this.array.slice(0).buffer);let t=new this.array.constructor(e.arrayBuffers[this.array.buffer._uuid]),n=new this.constructor(t,this.stride);return n.setUsage(this.usage),n}onUpload(e){return this.onUploadCallback=e,this}toJSON(e){e.arrayBuffers===void 0&&(e.arrayBuffers={}),this.array.buffer._uuid===void 0&&(this.array.buffer._uuid=kn()),e.arrayBuffers[this.array.buffer._uuid]===void 0&&(e.arrayBuffers[this.array.buffer._uuid]=Array.from(new Uint32Array(this.array.buffer)));let t={uuid:this.uuid,buffer:this.array.buffer._uuid,type:this.array.constructor.name,stride:this.stride};return t.usage=this.usage,t}},mn=new R,rs=class s{constructor(e,t,n,i=!1){this.isInterleavedBufferAttribute=!0,this.name="",this.data=e,this.itemSize=t,this.offset=n,this.normalized=i}get count(){return this.data.count}get array(){return this.data.array}set needsUpdate(e){this.data.needsUpdate=e}applyMatrix4(e){for(let t=0,n=this.data.count;t<n;t++)mn.fromBufferAttribute(this,t),mn.applyMatrix4(e),this.setXYZ(t,mn.x,mn.y,mn.z);return this}applyNormalMatrix(e){for(let t=0,n=this.count;t<n;t++)mn.fromBufferAttribute(this,t),mn.applyNormalMatrix(e),this.setXYZ(t,mn.x,mn.y,mn.z);return this}transformDirection(e){for(let t=0,n=this.count;t<n;t++)mn.fromBufferAttribute(this,t),mn.transformDirection(e),this.setXYZ(t,mn.x,mn.y,mn.z);return this}getComponent(e,t){let n=this.array[e*this.data.stride+this.offset+t];return this.normalized&&(n=ti(n,this.array)),n}setComponent(e,t,n){return this.normalized&&(n=wt(n,this.array)),this.data.array[e*this.data.stride+this.offset+t]=n,this}setX(e,t){return this.normalized&&(t=wt(t,this.array)),this.data.array[e*this.data.stride+this.offset]=t,this}setY(e,t){return this.normalized&&(t=wt(t,this.array)),this.data.array[e*this.data.stride+this.offset+1]=t,this}setZ(e,t){return this.normalized&&(t=wt(t,this.array)),this.data.array[e*this.data.stride+this.offset+2]=t,this}setW(e,t){return this.normalized&&(t=wt(t,this.array)),this.data.array[e*this.data.stride+this.offset+3]=t,this}getX(e){let t=this.data.array[e*this.data.stride+this.offset];return this.normalized&&(t=ti(t,this.array)),t}getY(e){let t=this.data.array[e*this.data.stride+this.offset+1];return this.normalized&&(t=ti(t,this.array)),t}getZ(e){let t=this.data.array[e*this.data.stride+this.offset+2];return this.normalized&&(t=ti(t,this.array)),t}getW(e){let t=this.data.array[e*this.data.stride+this.offset+3];return this.normalized&&(t=ti(t,this.array)),t}setXY(e,t,n){return e=e*this.data.stride+this.offset,this.normalized&&(t=wt(t,this.array),n=wt(n,this.array)),this.data.array[e+0]=t,this.data.array[e+1]=n,this}setXYZ(e,t,n,i){return e=e*this.data.stride+this.offset,this.normalized&&(t=wt(t,this.array),n=wt(n,this.array),i=wt(i,this.array)),this.data.array[e+0]=t,this.data.array[e+1]=n,this.data.array[e+2]=i,this}setXYZW(e,t,n,i,r){return e=e*this.data.stride+this.offset,this.normalized&&(t=wt(t,this.array),n=wt(n,this.array),i=wt(i,this.array),r=wt(r,this.array)),this.data.array[e+0]=t,this.data.array[e+1]=n,this.data.array[e+2]=i,this.data.array[e+3]=r,this}clone(e){if(e===void 0){oa("InterleavedBufferAttribute.clone(): Cloning an interleaved buffer attribute will de-interleave buffer data.");let t=[];for(let n=0;n<this.count;n++){let i=n*this.data.stride+this.offset;for(let r=0;r<this.itemSize;r++)t.push(this.data.array[i+r])}return new Ft(new this.array.constructor(t),this.itemSize,this.normalized)}else return e.interleavedBuffers===void 0&&(e.interleavedBuffers={}),e.interleavedBuffers[this.data.uuid]===void 0&&(e.interleavedBuffers[this.data.uuid]=this.data.clone(e)),new s(e.interleavedBuffers[this.data.uuid],this.itemSize,this.offset,this.normalized)}toJSON(e){if(e===void 0){oa("InterleavedBufferAttribute.toJSON(): Serializing an interleaved buffer attribute will de-interleave buffer data.");let t=[];for(let n=0;n<this.count;n++){let i=n*this.data.stride+this.offset;for(let r=0;r<this.itemSize;r++)t.push(this.data.array[i+r])}return{itemSize:this.itemSize,type:this.array.constructor.name,array:t,normalized:this.normalized}}else return e.interleavedBuffers===void 0&&(e.interleavedBuffers={}),e.interleavedBuffers[this.data.uuid]===void 0&&(e.interleavedBuffers[this.data.uuid]=this.data.toJSON(e)),{isInterleavedBufferAttribute:!0,itemSize:this.itemSize,data:this.data.uuid,offset:this.offset,normalized:this.normalized}}},hh=new R,hg=new R,ug=new Ze,ei=class{constructor(e=new R(1,0,0),t=0){this.isPlane=!0,this.normal=e,this.constant=t}set(e,t){return this.normal.copy(e),this.constant=t,this}setComponents(e,t,n,i){return this.normal.set(e,t,n),this.constant=i,this}setFromNormalAndCoplanarPoint(e,t){return this.normal.copy(e),this.constant=-t.dot(this.normal),this}setFromCoplanarPoints(e,t,n){let i=hh.subVectors(n,t).cross(hg.subVectors(e,t)).normalize();return this.setFromNormalAndCoplanarPoint(i,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){let e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,t){return t.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,t,n=!0){let i=e.delta(hh),r=this.normal.dot(i);if(r===0)return this.distanceToPoint(e.start)===0?t.copy(e.start):null;let a=-(e.start.dot(this.normal)+this.constant)/r;return n===!0&&(a<0||a>1)?null:t.copy(e.start).addScaledVector(i,a)}intersectsLine(e){let t=this.distanceToPoint(e.start),n=this.distanceToPoint(e.end);return t<0&&n>0||n<0&&t>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,t){let n=t||ug.getNormalMatrix(e),i=this.coplanarPoint(hh).applyMatrix4(e),r=this.normal.applyMatrix3(n).normalize();return this.constant=-i.dot(r),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}toJSON(){return{normal:this.normal.toArray(),constant:this.constant}}fromJSON(e){return this.normal.fromArray(e.normal),this.constant=e.constant,this}},dg=0,xn=class extends vi{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:dg++}),this.uuid=kn(),this.name="",this.type="Material",this.blending=Ir,this.side=wi,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=Gh,this.blendDst=Vh,this.blendEquation=Us,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new Me(0,0,0),this.blendAlpha=0,this.depthFunc=pr,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=Vf,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Xo,this.stencilZFail=Xo,this.stencilZPass=Xo,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(let t in e){let n=e[t];if(n===void 0){Le(`Material: parameter '${t}' has value of undefined.`);continue}let i=this[t];if(i===void 0){Le(`Material: '${t}' is not a property of THREE.${this.type}.`);continue}i&&i.isColor?i.set(n):i&&i.isVector2&&n&&n.isVector2||i&&i.isEuler&&n&&n.isEuler||i&&i.isVector3&&n&&n.isVector3?i.copy(n):this[t]=n}}toJSON(e){let t=e===void 0||typeof e=="string";t&&(e={textures:{},images:{}});let n={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,n.blending=this.blending,n.side=this.side,n.shadowSide=this.shadowSide,n.vertexColors=this.vertexColors,n.opacity=this.opacity,n.transparent=this.transparent,n.blendSrc=this.blendSrc,n.blendDst=this.blendDst,n.blendEquation=this.blendEquation,n.blendSrcAlpha=this.blendSrcAlpha,n.blendDstAlpha=this.blendDstAlpha,n.blendEquationAlpha=this.blendEquationAlpha,n.blendColor=this.blendColor.getHex(),n.blendAlpha=this.blendAlpha,n.depthFunc=this.depthFunc,n.depthTest=this.depthTest,n.depthWrite=this.depthWrite,n.colorWrite=this.colorWrite,n.clipIntersection=this.clipIntersection,n.clipShadows=this.clipShadows,n.stencilWriteMask=this.stencilWriteMask,n.stencilFunc=this.stencilFunc,n.stencilRef=this.stencilRef,n.stencilFuncMask=this.stencilFuncMask,n.stencilFail=this.stencilFail,n.stencilZFail=this.stencilZFail,n.stencilZPass=this.stencilZPass,n.stencilWrite=this.stencilWrite,n.polygonOffset=this.polygonOffset,n.polygonOffsetFactor=this.polygonOffsetFactor,n.polygonOffsetUnits=this.polygonOffsetUnits,n.dithering=this.dithering,n.alphaTest=this.alphaTest,n.alphaHash=this.alphaHash,n.alphaToCoverage=this.alphaToCoverage,n.premultipliedAlpha=this.premultipliedAlpha,n.forceSinglePass=this.forceSinglePass,n.allowOverride=this.allowOverride,n.visible=this.visible,n.toneMapped=this.toneMapped,n.name=this.name,this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.sheenColorMap&&this.sheenColorMap.isTexture&&(n.sheenColorMap=this.sheenColorMap.toJSON(e).uuid),this.sheenRoughnessMap&&this.sheenRoughnessMap.isTexture&&(n.sheenRoughnessMap=this.sheenRoughnessMap.toJSON(e).uuid),this.dispersion!==void 0&&(n.dispersion=this.dispersion),this.retroreflectivity!==void 0&&(n.retroreflectivity=this.retroreflectivity),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(e).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(e).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(e).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(e).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(e).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),Array.isArray(this.clippingPlanes)&&this.clippingPlanes.length>0&&(n.clippingPlanes=this.clippingPlanes.map(r=>r.toJSON())),this.rotation!==void 0&&(n.rotation=this.rotation),this.depthPacking!==void 0&&(n.depthPacking=this.depthPacking),this.linewidth!==void 0&&(n.linewidth=this.linewidth),this.linecap!==void 0&&(n.linecap=this.linecap),this.linejoin!==void 0&&(n.linejoin=this.linejoin),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.wireframe!==void 0&&(n.wireframe=this.wireframe),this.wireframeLinewidth!==void 0&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!==void 0&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!==void 0&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading!==void 0&&(n.flatShading=this.flatShading),this.fog!==void 0&&(n.fog=this.fog),Object.keys(this.userData).length>0&&(n.userData=this.userData);function i(r){let a=[];for(let o in r){let c=r[o];delete c.metadata,a.push(c)}return a}if(t){let r=i(e.textures),a=i(e.images);r.length>0&&(n.textures=r),a.length>0&&(n.images=a)}return n}fromJSON(e,t){if(e.uuid!==void 0&&(this.uuid=e.uuid),e.name!==void 0&&(this.name=e.name),e.color!==void 0&&this.color!==void 0&&this.color.setHex(e.color),e.roughness!==void 0&&(this.roughness=e.roughness),e.metalness!==void 0&&(this.metalness=e.metalness),e.sheen!==void 0&&(this.sheen=e.sheen),e.sheenColor!==void 0&&(this.sheenColor=new Me().setHex(e.sheenColor)),e.sheenRoughness!==void 0&&(this.sheenRoughness=e.sheenRoughness),e.emissive!==void 0&&this.emissive!==void 0&&this.emissive.setHex(e.emissive),e.specular!==void 0&&this.specular!==void 0&&this.specular.setHex(e.specular),e.specularIntensity!==void 0&&(this.specularIntensity=e.specularIntensity),e.specularColor!==void 0&&this.specularColor!==void 0&&this.specularColor.setHex(e.specularColor),e.shininess!==void 0&&(this.shininess=e.shininess),e.clearcoat!==void 0&&(this.clearcoat=e.clearcoat),e.clearcoatRoughness!==void 0&&(this.clearcoatRoughness=e.clearcoatRoughness),e.dispersion!==void 0&&(this.dispersion=e.dispersion),e.retroreflectivity!==void 0&&(this.retroreflectivity=e.retroreflectivity),e.iridescence!==void 0&&(this.iridescence=e.iridescence),e.iridescenceIOR!==void 0&&(this.iridescenceIOR=e.iridescenceIOR),e.iridescenceThicknessRange!==void 0&&(this.iridescenceThicknessRange=e.iridescenceThicknessRange),e.transmission!==void 0&&(this.transmission=e.transmission),e.thickness!==void 0&&(this.thickness=e.thickness),e.attenuationDistance!==void 0&&(this.attenuationDistance=e.attenuationDistance),e.attenuationColor!==void 0&&this.attenuationColor!==void 0&&this.attenuationColor.setHex(e.attenuationColor),e.anisotropy!==void 0&&(this.anisotropy=e.anisotropy),e.anisotropyRotation!==void 0&&(this.anisotropyRotation=e.anisotropyRotation),e.fog!==void 0&&(this.fog=e.fog),e.flatShading!==void 0&&(this.flatShading=e.flatShading),e.blending!==void 0&&(this.blending=e.blending),e.combine!==void 0&&(this.combine=e.combine),e.side!==void 0&&(this.side=e.side),e.shadowSide!==void 0&&(this.shadowSide=e.shadowSide),e.opacity!==void 0&&(this.opacity=e.opacity),e.transparent!==void 0&&(this.transparent=e.transparent),e.alphaTest!==void 0&&(this.alphaTest=e.alphaTest),e.alphaHash!==void 0&&(this.alphaHash=e.alphaHash),e.depthFunc!==void 0&&(this.depthFunc=e.depthFunc),e.depthTest!==void 0&&(this.depthTest=e.depthTest),e.depthWrite!==void 0&&(this.depthWrite=e.depthWrite),e.colorWrite!==void 0&&(this.colorWrite=e.colorWrite),e.clippingPlanes!==void 0&&(this.clippingPlanes=e.clippingPlanes.map(n=>new ei().fromJSON(n))),e.clipIntersection!==void 0&&(this.clipIntersection=e.clipIntersection),e.clipShadows!==void 0&&(this.clipShadows=e.clipShadows),e.depthPacking!==void 0&&(this.depthPacking=e.depthPacking),e.blendSrc!==void 0&&(this.blendSrc=e.blendSrc),e.blendDst!==void 0&&(this.blendDst=e.blendDst),e.blendEquation!==void 0&&(this.blendEquation=e.blendEquation),e.blendSrcAlpha!==void 0&&(this.blendSrcAlpha=e.blendSrcAlpha),e.blendDstAlpha!==void 0&&(this.blendDstAlpha=e.blendDstAlpha),e.blendEquationAlpha!==void 0&&(this.blendEquationAlpha=e.blendEquationAlpha),e.blendColor!==void 0&&this.blendColor!==void 0&&this.blendColor.setHex(e.blendColor),e.blendAlpha!==void 0&&(this.blendAlpha=e.blendAlpha),e.stencilWriteMask!==void 0&&(this.stencilWriteMask=e.stencilWriteMask),e.stencilFunc!==void 0&&(this.stencilFunc=e.stencilFunc),e.stencilRef!==void 0&&(this.stencilRef=e.stencilRef),e.stencilFuncMask!==void 0&&(this.stencilFuncMask=e.stencilFuncMask),e.stencilFail!==void 0&&(this.stencilFail=e.stencilFail),e.stencilZFail!==void 0&&(this.stencilZFail=e.stencilZFail),e.stencilZPass!==void 0&&(this.stencilZPass=e.stencilZPass),e.stencilWrite!==void 0&&(this.stencilWrite=e.stencilWrite),e.wireframe!==void 0&&(this.wireframe=e.wireframe),e.wireframeLinewidth!==void 0&&(this.wireframeLinewidth=e.wireframeLinewidth),e.wireframeLinecap!==void 0&&(this.wireframeLinecap=e.wireframeLinecap),e.wireframeLinejoin!==void 0&&(this.wireframeLinejoin=e.wireframeLinejoin),e.rotation!==void 0&&(this.rotation=e.rotation),e.linewidth!==void 0&&(this.linewidth=e.linewidth),e.linecap!==void 0&&(this.linecap=e.linecap),e.linejoin!==void 0&&(this.linejoin=e.linejoin),e.dashSize!==void 0&&(this.dashSize=e.dashSize),e.gapSize!==void 0&&(this.gapSize=e.gapSize),e.scale!==void 0&&(this.scale=e.scale),e.polygonOffset!==void 0&&(this.polygonOffset=e.polygonOffset),e.polygonOffsetFactor!==void 0&&(this.polygonOffsetFactor=e.polygonOffsetFactor),e.polygonOffsetUnits!==void 0&&(this.polygonOffsetUnits=e.polygonOffsetUnits),e.dithering!==void 0&&(this.dithering=e.dithering),e.alphaToCoverage!==void 0&&(this.alphaToCoverage=e.alphaToCoverage),e.premultipliedAlpha!==void 0&&(this.premultipliedAlpha=e.premultipliedAlpha),e.forceSinglePass!==void 0&&(this.forceSinglePass=e.forceSinglePass),e.allowOverride!==void 0&&(this.allowOverride=e.allowOverride),e.visible!==void 0&&(this.visible=e.visible),e.toneMapped!==void 0&&(this.toneMapped=e.toneMapped),e.userData!==void 0&&(this.userData=e.userData),e.vertexColors!==void 0&&(typeof e.vertexColors=="number"?this.vertexColors=e.vertexColors>0:this.vertexColors=e.vertexColors),e.size!==void 0&&(this.size=e.size),e.sizeAttenuation!==void 0&&(this.sizeAttenuation=e.sizeAttenuation),e.map!==void 0&&(this.map=t[e.map]||null),e.matcap!==void 0&&(this.matcap=t[e.matcap]||null),e.alphaMap!==void 0&&(this.alphaMap=t[e.alphaMap]||null),e.bumpMap!==void 0&&(this.bumpMap=t[e.bumpMap]||null),e.bumpScale!==void 0&&(this.bumpScale=e.bumpScale),e.normalMap!==void 0&&(this.normalMap=t[e.normalMap]||null),e.normalMapType!==void 0&&(this.normalMapType=e.normalMapType),e.normalScale!==void 0){let n=e.normalScale;Array.isArray(n)===!1&&(n=[n,n]),this.normalScale=new ne().fromArray(n)}return e.displacementMap!==void 0&&(this.displacementMap=t[e.displacementMap]||null),e.displacementScale!==void 0&&(this.displacementScale=e.displacementScale),e.displacementBias!==void 0&&(this.displacementBias=e.displacementBias),e.roughnessMap!==void 0&&(this.roughnessMap=t[e.roughnessMap]||null),e.metalnessMap!==void 0&&(this.metalnessMap=t[e.metalnessMap]||null),e.emissiveMap!==void 0&&(this.emissiveMap=t[e.emissiveMap]||null),e.emissiveIntensity!==void 0&&(this.emissiveIntensity=e.emissiveIntensity),e.specularMap!==void 0&&(this.specularMap=t[e.specularMap]||null),e.specularIntensityMap!==void 0&&(this.specularIntensityMap=t[e.specularIntensityMap]||null),e.specularColorMap!==void 0&&(this.specularColorMap=t[e.specularColorMap]||null),e.envMap!==void 0&&(this.envMap=t[e.envMap]||null),e.envMapRotation!==void 0&&this.envMapRotation.fromArray(e.envMapRotation),e.envMapIntensity!==void 0&&(this.envMapIntensity=e.envMapIntensity),e.reflectivity!==void 0&&(this.reflectivity=e.reflectivity),e.refractionRatio!==void 0&&(this.refractionRatio=e.refractionRatio),e.lightMap!==void 0&&(this.lightMap=t[e.lightMap]||null),e.lightMapIntensity!==void 0&&(this.lightMapIntensity=e.lightMapIntensity),e.aoMap!==void 0&&(this.aoMap=t[e.aoMap]||null),e.aoMapIntensity!==void 0&&(this.aoMapIntensity=e.aoMapIntensity),e.gradientMap!==void 0&&(this.gradientMap=t[e.gradientMap]||null),e.clearcoatMap!==void 0&&(this.clearcoatMap=t[e.clearcoatMap]||null),e.clearcoatRoughnessMap!==void 0&&(this.clearcoatRoughnessMap=t[e.clearcoatRoughnessMap]||null),e.clearcoatNormalMap!==void 0&&(this.clearcoatNormalMap=t[e.clearcoatNormalMap]||null),e.clearcoatNormalScale!==void 0&&(this.clearcoatNormalScale=new ne().fromArray(e.clearcoatNormalScale)),e.iridescenceMap!==void 0&&(this.iridescenceMap=t[e.iridescenceMap]||null),e.iridescenceThicknessMap!==void 0&&(this.iridescenceThicknessMap=t[e.iridescenceThicknessMap]||null),e.transmissionMap!==void 0&&(this.transmissionMap=t[e.transmissionMap]||null),e.thicknessMap!==void 0&&(this.thicknessMap=t[e.thicknessMap]||null),e.anisotropyMap!==void 0&&(this.anisotropyMap=t[e.anisotropyMap]||null),e.sheenColorMap!==void 0&&(this.sheenColorMap=t[e.sheenColorMap]||null),e.sheenRoughnessMap!==void 0&&(this.sheenRoughnessMap=t[e.sheenRoughnessMap]||null),this}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;let t=e.clippingPlanes,n=null;if(t!==null){let i=t.length;n=new Array(i);for(let r=0;r!==i;++r)n[r]=t[r].clone()}return this.clippingPlanes=n,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.allowOverride=e.allowOverride,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}},vn=class extends xn{constructor(e){super(),this.isSpriteMaterial=!0,this.type="SpriteMaterial",this.color=new Me(16777215),this.map=null,this.alphaMap=null,this.rotation=0,this.sizeAttenuation=!0,this.transparent=!0,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.alphaMap=e.alphaMap,this.rotation=e.rotation,this.sizeAttenuation=e.sizeAttenuation,this.fog=e.fog,this}},sr,Zr=new R,rr=new R,ar=new R,or=new ne,Jr=new ne,ep=new je,_o=new R,$r=new R,yo=new R,Fd=new ne,uh=new ne,Od=new ne,Cn=class extends ft{constructor(e=new vn){if(super(),this.isSprite=!0,this.type="Sprite",sr===void 0){sr=new tt;let t=new Float32Array([-.5,-.5,0,0,0,.5,-.5,0,1,0,.5,.5,0,1,1,-.5,.5,0,0,1]),n=new Cs(t,5);sr.setIndex([0,1,2,0,2,3]),sr.setAttribute("position",new rs(n,3,0,!1)),sr.setAttribute("uv",new rs(n,2,3,!1))}this.geometry=sr,this.material=e,this.center=new ne(.5,.5),this.count=1}intersectsFrustum(e){return e.intersectsSprite(this)}raycast(e,t){e.camera===null&&He('Sprite: "Raycaster.camera" needs to be set in order to raycast against sprites.'),rr.setFromMatrixScale(this.matrixWorld),ep.copy(e.camera.matrixWorld),this.modelViewMatrix.multiplyMatrices(e.camera.matrixWorldInverse,this.matrixWorld),ar.setFromMatrixPosition(this.modelViewMatrix),e.camera.isPerspectiveCamera&&this.material.sizeAttenuation===!1&&rr.multiplyScalar(-ar.z);let n=this.material.rotation,i,r;n!==0&&(r=Math.cos(n),i=Math.sin(n));let a=this.center;vo(_o.set(-.5,-.5,0),ar,a,rr,i,r),vo($r.set(.5,-.5,0),ar,a,rr,i,r),vo(yo.set(.5,.5,0),ar,a,rr,i,r),Fd.set(0,0),uh.set(1,0),Od.set(1,1);let o=e.ray.intersectTriangle(_o,$r,yo,!1,Zr);if(o===null&&(vo($r.set(-.5,.5,0),ar,a,rr,i,r),uh.set(0,1),o=e.ray.intersectTriangle(_o,yo,$r,!1,Zr),o===null))return;let c=e.ray.origin.distanceTo(Zr);c<e.near||c>e.far||t.push({distance:c,point:Zr.clone(),uv:mi.getInterpolation(Zr,_o,$r,yo,Fd,uh,Od,new ne),face:null,object:this})}copy(e,t){return super.copy(e,t),e.center!==void 0&&this.center.copy(e.center),this.material=e.material,this}};function vo(s,e,t,n,i,r){or.subVectors(s,t).addScalar(.5).multiply(n),i!==void 0?(Jr.x=r*or.x-i*or.y,Jr.y=i*or.x+r*or.y):Jr.copy(or),s.copy(e),s.x+=Jr.x,s.y+=Jr.y,s.applyMatrix4(ep)}var Di=new R,dh=new R,Mo=new R,So=new R,Rs=class{constructor(e=new R,t=new R(0,0,-1)){this.origin=e,this.direction=t}set(e,t){return this.origin.copy(e),this.direction.copy(t),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,t){return t.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,Di)),this}closestPointToPoint(e,t){t.subVectors(e,this.origin);let n=t.dot(this.direction);return n<0?t.copy(this.origin):t.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){let t=Di.subVectors(e,this.origin).dot(this.direction);return t<0?this.origin.distanceToSquared(e):(Di.copy(this.origin).addScaledVector(this.direction,t),Di.distanceToSquared(e))}distanceSqToSegment(e,t,n,i){dh.copy(e).add(t).multiplyScalar(.5),Mo.copy(t).sub(e).normalize(),So.copy(this.origin).sub(dh);let r=e.distanceTo(t)*.5,a=-this.direction.dot(Mo),o=So.dot(this.direction),c=-So.dot(Mo),l=So.lengthSq(),h=Math.abs(1-a*a),u,d,p,g;if(h>0)if(u=a*c-o,d=a*o-c,g=r*h,u>=0)if(d>=-g)if(d<=g){let v=1/h;u*=v,d*=v,p=u*(u+a*d+2*o)+d*(a*u+d+2*c)+l}else d=r,u=Math.max(0,-(a*d+o)),p=-u*u+d*(d+2*c)+l;else d=-r,u=Math.max(0,-(a*d+o)),p=-u*u+d*(d+2*c)+l;else d<=-g?(u=Math.max(0,-(-a*r+o)),d=u>0?-r:Math.min(Math.max(-r,-c),r),p=-u*u+d*(d+2*c)+l):d<=g?(u=0,d=Math.min(Math.max(-r,-c),r),p=d*(d+2*c)+l):(u=Math.max(0,-(a*r+o)),d=u>0?r:Math.min(Math.max(-r,-c),r),p=-u*u+d*(d+2*c)+l);else d=a>0?-r:r,u=Math.max(0,-(a*d+o)),p=-u*u+d*(d+2*c)+l;return n&&n.copy(this.origin).addScaledVector(this.direction,u),i&&i.copy(dh).addScaledVector(Mo,d),p}intersectSphere(e,t){if(e.radius<0)return null;Di.subVectors(e.center,this.origin);let n=Di.dot(this.direction),i=Di.dot(Di)-n*n,r=e.radius*e.radius;if(i>r)return null;let a=Math.sqrt(r-i),o=n-a,c=n+a;return c<0?null:o<0?this.at(c,t):this.at(o,t)}intersectsSphere(e){return e.radius<0?!1:this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){let t=e.normal.dot(this.direction);if(t===0)return e.distanceToPoint(this.origin)===0?0:null;let n=-(this.origin.dot(e.normal)+e.constant)/t;return n>=0?n:null}intersectPlane(e,t){let n=this.distanceToPlane(e);return n===null?null:this.at(n,t)}intersectsPlane(e){let t=e.distanceToPoint(this.origin);return t===0||e.normal.dot(this.direction)*t<0}intersectBox(e,t){let n,i,r,a,o,c,l=1/this.direction.x,h=1/this.direction.y,u=1/this.direction.z,d=this.origin;return l>=0?(n=(e.min.x-d.x)*l,i=(e.max.x-d.x)*l):(n=(e.max.x-d.x)*l,i=(e.min.x-d.x)*l),h>=0?(r=(e.min.y-d.y)*h,a=(e.max.y-d.y)*h):(r=(e.max.y-d.y)*h,a=(e.min.y-d.y)*h),n>a||r>i||((r>n||isNaN(n))&&(n=r),(a<i||isNaN(i))&&(i=a),u>=0?(o=(e.min.z-d.z)*u,c=(e.max.z-d.z)*u):(o=(e.max.z-d.z)*u,c=(e.min.z-d.z)*u),n>c||o>i)||((o>n||n!==n)&&(n=o),(c<i||i!==i)&&(i=c),i<0)?null:this.at(n>=0?n:i,t)}intersectsBox(e){return this.intersectBox(e,Di)!==null}intersectTriangle(e,t,n,i,r){let a=this.origin,o=this.direction,c=o.x,l=o.y,h=o.z,u=e.x-a.x,d=e.y-a.y,p=e.z-a.z,g=t.x-a.x,v=t.y-a.y,f=t.z-a.z,m=n.x-a.x,_=n.y-a.y,b=n.z-a.z,x=Math.abs(c),T=Math.abs(l),S=Math.abs(h),A,y,E,I,L,F,V,D,B,X,W,re;if(x>=T&&x>=S?(E=c,F=u,B=g,re=m,c>=0?(A=l,y=h,I=d,L=p,V=v,D=f,X=_,W=b):(A=h,y=l,I=p,L=d,V=f,D=v,X=b,W=_)):T>=S?(E=l,F=d,B=v,re=_,l>=0?(A=h,y=c,I=p,L=u,V=f,D=g,X=b,W=m):(A=c,y=h,I=u,L=p,V=g,D=f,X=m,W=b)):(E=h,F=p,B=f,re=b,h>=0?(A=c,y=l,I=u,L=d,V=g,D=v,X=m,W=_):(A=l,y=c,I=d,L=u,V=v,D=g,X=_,W=m)),E===0)return null;let q=A/E,j=y/E,te=1/E,Ne=I-q*F,Ae=L-j*F,vt=V-q*B,ct=D-j*B,mt=X-q*re,Z=W-j*re,Q=mt*ct-Z*vt,_e=Ne*Z-Ae*mt,We=vt*Ae-ct*Ne;if(i){if(Q<0||_e<0||We<0)return null}else if((Q<0||_e<0||We<0)&&(Q>0||_e>0||We>0))return null;let be=Q+_e+We;if(be===0)return null;let Xe=te*(Q*F+_e*B+We*re);return(be>0?Xe<0:Xe>0)?null:this.at(Xe/be,r)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}},Ye=class extends xn{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new Me(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Oi,this.combine=Hh,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}},Bd=new je,Ms=new Rs,bo=new yn,kd=new R,To=new R,wo=new R,Ao=new R,fh=new R,Eo=new R,zd=new R,Co=new R,Ee=class extends ft{constructor(e=new tt,t=new Ye){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){let t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){let i=t[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=i.length;r<a;r++){let o=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}getVertexPosition(e,t){let n=this.geometry,i=n.attributes.position,r=n.morphAttributes.position,a=n.morphTargetsRelative;t.fromBufferAttribute(i,e);let o=this.morphTargetInfluences;if(r&&o){Eo.set(0,0,0);for(let c=0,l=r.length;c<l;c++){let h=o[c],u=r[c];h!==0&&(fh.fromBufferAttribute(u,e),a?Eo.addScaledVector(fh,h):Eo.addScaledVector(fh.sub(t),h))}t.add(Eo)}return t}intersectsFrustum(e){return e.intersectsObject(this)}raycast(e,t){let n=this.geometry,i=this.material,r=this.matrixWorld;i!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),bo.copy(n.boundingSphere),bo.applyMatrix4(r),Ms.copy(e.ray).recast(e.near),!(bo.containsPoint(Ms.origin)===!1&&(Ms.intersectSphere(bo,kd)===null||Ms.origin.distanceToSquared(kd)>(e.far-e.near)**2))&&(Bd.copy(r).invert(),Ms.copy(e.ray).applyMatrix4(Bd),!(n.boundingBox!==null&&Ms.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(e,t,Ms)))}_computeIntersections(e,t,n){let i,r=this.geometry,a=this.material,o=r.index,c=r.attributes.position,l=r.attributes.uv,h=r.attributes.uv1,u=r.attributes.normal,d=r.groups,p=r.drawRange;if(o!==null)if(Array.isArray(a))for(let g=0,v=d.length;g<v;g++){let f=d[g],m=a[f.materialIndex],_=Math.max(f.start,p.start),b=Math.min(o.count,Math.min(f.start+f.count,p.start+p.count));for(let x=_,T=b;x<T;x+=3){let S=o.getX(x),A=o.getX(x+1),y=o.getX(x+2);i=Ro(this,m,e,n,l,h,u,S,A,y),i&&(i.faceIndex=Math.floor(x/3),i.face.materialIndex=f.materialIndex,t.push(i))}}else{let g=Math.max(0,p.start),v=Math.min(o.count,p.start+p.count);for(let f=g,m=v;f<m;f+=3){let _=o.getX(f),b=o.getX(f+1),x=o.getX(f+2);i=Ro(this,a,e,n,l,h,u,_,b,x),i&&(i.faceIndex=Math.floor(f/3),t.push(i))}}else if(c!==void 0)if(Array.isArray(a))for(let g=0,v=d.length;g<v;g++){let f=d[g],m=a[f.materialIndex],_=Math.max(f.start,p.start),b=Math.min(c.count,Math.min(f.start+f.count,p.start+p.count));for(let x=_,T=b;x<T;x+=3){let S=x,A=x+1,y=x+2;i=Ro(this,m,e,n,l,h,u,S,A,y),i&&(i.faceIndex=Math.floor(x/3),i.face.materialIndex=f.materialIndex,t.push(i))}}else{let g=Math.max(0,p.start),v=Math.min(c.count,p.start+p.count);for(let f=g,m=v;f<m;f+=3){let _=f,b=f+1,x=f+2;i=Ro(this,a,e,n,l,h,u,_,b,x),i&&(i.faceIndex=Math.floor(f/3),t.push(i))}}}};function fg(s,e,t,n,i,r,a,o){let c;if(e.side===qt?c=n.intersectTriangle(a,r,i,!0,o):c=n.intersectTriangle(i,r,a,e.side===wi,o),c===null)return null;Co.copy(o),Co.applyMatrix4(s.matrixWorld);let l=t.ray.origin.distanceTo(Co);return l<t.near||l>t.far?null:{distance:l,point:Co.clone(),object:s}}function Ro(s,e,t,n,i,r,a,o,c,l){s.getVertexPosition(o,To),s.getVertexPosition(c,wo),s.getVertexPosition(l,Ao);let h=fg(s,e,t,n,To,wo,Ao,zd);if(h){let u=new R;mi.getBarycoord(zd,To,wo,Ao,u),i&&(h.uv=mi.getInterpolatedAttribute(i,o,c,l,u,new ne)),r&&(h.uv1=mi.getInterpolatedAttribute(r,o,c,l,u,new ne)),a&&(h.normal=mi.getInterpolatedAttribute(a,o,c,l,u,new R),h.normal.dot(n.direction)>0&&h.normal.multiplyScalar(-1));let d={a:o,b:c,c:l,normal:new R,materialIndex:0};mi.getNormal(To,wo,Ao,d.normal),h.face=d,h.barycoord=u}return h}var jr=new At,Gd=new At,Vd=new At,pg=new At,Hd=new je,Io=new R,ph=new yn,Wd=new je,mh=new Rs,fa=class extends Ee{constructor(e,t){super(e,t),this.isSkinnedMesh=!0,this.type="SkinnedMesh",this.bindMode=bh,this.bindMatrix=new je,this.bindMatrixInverse=new je,this.boundingBox=null,this.boundingSphere=null}computeBoundingBox(){let e=this.geometry;this.boundingBox===null&&(this.boundingBox=new En),this.boundingBox.makeEmpty();let t=e.getAttribute("position");for(let n=0;n<t.count;n++)this.getVertexPosition(n,Io),this.boundingBox.expandByPoint(Io)}computeBoundingSphere(){let e=this.geometry;this.boundingSphere===null&&(this.boundingSphere=new yn),this.boundingSphere.makeEmpty();let t=e.getAttribute("position");for(let n=0;n<t.count;n++)this.getVertexPosition(n,Io),this.boundingSphere.expandByPoint(Io)}copy(e,t){return super.copy(e,t),this.bindMode=e.bindMode,this.bindMatrix.copy(e.bindMatrix),this.bindMatrixInverse.copy(e.bindMatrixInverse),this.skeleton=e.skeleton,e.boundingBox!==null&&(this.boundingBox=e.boundingBox.clone()),e.boundingSphere!==null&&(this.boundingSphere=e.boundingSphere.clone()),this}raycast(e,t){let n=this.material,i=this.matrixWorld;n!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),ph.copy(this.boundingSphere),ph.applyMatrix4(i),e.ray.intersectsSphere(ph)!==!1&&(Wd.copy(i).invert(),mh.copy(e.ray).applyMatrix4(Wd),!(this.boundingBox!==null&&mh.intersectsBox(this.boundingBox)===!1)&&this._computeIntersections(e,t,mh)))}getVertexPosition(e,t){return super.getVertexPosition(e,t),this.applyBoneTransform(e,t),t}bind(e,t){this.skeleton=e,t===void 0&&(this.updateMatrixWorld(!0),this.skeleton.calculateInverses(),t=this.matrixWorld),this.bindMatrix.copy(t),this.bindMatrixInverse.copy(t).invert()}pose(){this.skeleton.pose()}normalizeSkinWeights(){let e=new At,t=this.geometry.attributes.skinWeight;for(let n=0,i=t.count;n<i;n++){e.fromBufferAttribute(t,n);let r=1/e.manhattanLength();r!==1/0?e.multiplyScalar(r):e.set(1,0,0,0),t.setXYZW(n,e.x,e.y,e.z,e.w)}}updateMatrixWorld(e){super.updateMatrixWorld(e),this.bindMode===bh?this.bindMatrixInverse.copy(this.matrixWorld).invert():this.bindMode===Bf?this.bindMatrixInverse.copy(this.bindMatrix).invert():Le("SkinnedMesh: Unrecognized bindMode: "+this.bindMode)}applyBoneTransform(e,t){let n=this.skeleton,i=this.geometry;Gd.fromBufferAttribute(i.attributes.skinIndex,e),Vd.fromBufferAttribute(i.attributes.skinWeight,e),t.isVector4?(jr.copy(t),t.set(0,0,0,0)):(jr.set(...t,1),t.set(0,0,0)),jr.applyMatrix4(this.bindMatrix);for(let r=0;r<4;r++){let a=Vd.getComponent(r);if(a!==0){let o=Gd.getComponent(r);Hd.multiplyMatrices(n.bones[o].matrixWorld,n.boneInverses[o]),t.addScaledVector(pg.copy(jr).applyMatrix4(Hd),a)}}return t.isVector4&&(t.w=jr.w),t.applyMatrix4(this.bindMatrixInverse)}},Mr=class extends ft{constructor(){super(),this.isBone=!0,this.type="Bone"}},Sr=class extends jt{constructor(e=null,t=1,n=1,i,r,a,o,c,l=Wt,h=Wt,u,d){super(null,a,o,c,l,h,i,r,u,d),this.isDataTexture=!0,this.image={data:e,width:t,height:n},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}},Xd=new je,mg=new je,pa=class s{constructor(e=[],t=[]){this.uuid=kn(),this.bones=e.slice(0),this.boneInverses=t,this.boneMatrices=null,this.boneTexture=null,this.init()}init(){let e=this.bones,t=this.boneInverses;if(this.boneMatrices=new Float32Array(e.length*16),t.length===0)this.calculateInverses();else if(e.length!==t.length){Le("Skeleton: Number of inverse bone matrices does not match amount of bones."),this.boneInverses=[];for(let n=0,i=this.bones.length;n<i;n++)this.boneInverses.push(new je)}}calculateInverses(){this.boneInverses.length=0;for(let e=0,t=this.bones.length;e<t;e++){let n=new je;this.bones[e]&&n.copy(this.bones[e].matrixWorld).invert(),this.boneInverses.push(n)}}pose(){for(let e=0,t=this.bones.length;e<t;e++){let n=this.bones[e];n&&n.matrixWorld.copy(this.boneInverses[e]).invert()}for(let e=0,t=this.bones.length;e<t;e++){let n=this.bones[e];n&&(n.parent&&n.parent.isBone?(n.matrix.copy(n.parent.matrixWorld).invert(),n.matrix.multiply(n.matrixWorld)):n.matrix.copy(n.matrixWorld),n.matrix.decompose(n.position,n.quaternion,n.scale))}}update(){let e=this.bones,t=this.boneInverses,n=this.boneMatrices,i=this.boneTexture;for(let r=0,a=e.length;r<a;r++){let o=e[r]?e[r].matrixWorld:mg;Xd.multiplyMatrices(o,t[r]),Xd.toArray(n,r*16)}i!==null&&(i.needsUpdate=!0)}clone(){return new s(this.bones,this.boneInverses)}computeBoneTexture(){let e=Math.sqrt(this.bones.length*4);e=Math.ceil(e/4)*4,e=Math.max(e,4);let t=new Float32Array(e*e*4);t.set(this.boneMatrices);let n=new Sr(t,e,e,Un,Dn);return n.needsUpdate=!0,this.boneMatrices=t,this.boneTexture=n,this}getBoneByName(e){for(let t=0,n=this.bones.length;t<n;t++){let i=this.bones[t];if(i.name===e)return i}}dispose(){this.boneTexture!==null&&(this.boneTexture.dispose(),this.boneTexture=null)}fromJSON(e,t){this.uuid=e.uuid;for(let n=0,i=e.bones.length;n<i;n++){let r=e.bones[n],a=t[r];a===void 0&&(Le("Skeleton: No bone found with UUID:",r),a=new Mr),this.bones.push(a),this.boneInverses.push(new je().fromArray(e.boneInverses[n]))}return this.init(),this}toJSON(){let e={metadata:{version:4.7,type:"Skeleton",generator:"Skeleton.toJSON"},bones:[],boneInverses:[]};e.uuid=this.uuid;let t=this.bones,n=this.boneInverses;for(let i=0,r=t.length;i<r;i++){let a=t[i];e.bones.push(a.uuid);let o=n[i];e.boneInverses.push(o.toArray())}return e}},Bi=class extends Ft{constructor(e,t,n,i=1){super(e,t,n),this.isInstancedBufferAttribute=!0,this.meshPerAttribute=i}copy(e){return super.copy(e),this.meshPerAttribute=e.meshPerAttribute,this}toJSON(){let e=super.toJSON();return e.meshPerAttribute=this.meshPerAttribute,e.isInstancedBufferAttribute=!0,e}},lr=new je,qd=new je,Po=[],Yd=new En,gg=new je,Qr=new Ee,ea=new yn,un=class extends Ee{constructor(e,t,n){super(e,t),this.isInstancedMesh=!0,this.instanceMatrix=new Bi(new Float32Array(n*16),16),this.instanceColor=null,this.morphTexture=null,this.count=n,this.boundingBox=null,this.boundingSphere=null;for(let i=0;i<n;i++)this.setMatrixAt(i,gg)}computeBoundingBox(){let e=this.geometry,t=this.count;this.boundingBox===null&&(this.boundingBox=new En),e.boundingBox===null&&e.computeBoundingBox(),this.boundingBox.makeEmpty();for(let n=0;n<t;n++)this.getMatrixAt(n,lr),Yd.copy(e.boundingBox).applyMatrix4(lr),this.boundingBox.union(Yd)}computeBoundingSphere(){let e=this.geometry,t=this.count;this.boundingSphere===null&&(this.boundingSphere=new yn),e.boundingSphere===null&&e.computeBoundingSphere(),this.boundingSphere.makeEmpty();for(let n=0;n<t;n++)this.getMatrixAt(n,lr),ea.copy(e.boundingSphere).applyMatrix4(lr),this.boundingSphere.union(ea)}copy(e,t){return super.copy(e,t),this.instanceMatrix.copy(e.instanceMatrix),e.morphTexture!==null&&(this.morphTexture=e.morphTexture.clone()),e.instanceColor!==null&&(this.instanceColor=e.instanceColor.clone()),this.count=e.count,e.boundingBox!==null&&(this.boundingBox=e.boundingBox.clone()),e.boundingSphere!==null&&(this.boundingSphere=e.boundingSphere.clone()),this}getColorAt(e,t){return this.instanceColor===null?t.setRGB(1,1,1):t.fromArray(this.instanceColor.array,e*3)}getMatrixAt(e,t){return t.fromArray(this.instanceMatrix.array,e*16)}getMorphAt(e,t){let n=t.morphTargetInfluences,i=this.morphTexture.source.data.data,r=n.length+1,a=e*r+1;for(let o=0;o<n.length;o++)n[o]=i[a+o]}raycast(e,t){let n=this.matrixWorld,i=this.count;if(Qr.geometry=this.geometry,Qr.material=this.material,Qr.material!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),ea.copy(this.boundingSphere),ea.applyMatrix4(n),e.ray.intersectsSphere(ea)!==!1))for(let r=0;r<i;r++){this.getMatrixAt(r,lr),qd.multiplyMatrices(n,lr),Qr.matrixWorld=qd,Qr.raycast(e,Po);for(let a=0,o=Po.length;a<o;a++){let c=Po[a];c.instanceId=r,c.object=this,t.push(c)}Po.length=0}}setColorAt(e,t){return this.instanceColor===null&&(this.instanceColor=new Bi(new Float32Array(this.instanceMatrix.count*3).fill(1),3)),t.toArray(this.instanceColor.array,e*3),this}setMatrixAt(e,t){return t.toArray(this.instanceMatrix.array,e*16),this}setMorphAt(e,t){let n=t.morphTargetInfluences,i=n.length+1;this.morphTexture===null&&(this.morphTexture=new Sr(new Float32Array(i*this.count),i,this.count,El,Dn));let r=this.morphTexture.source.data.data,a=0;for(let l=0;l<n.length;l++)a+=n[l];let o=this.geometry.morphTargetsRelative?1:1-a,c=i*e;return r[c]=o,r.set(n,c+1),this}updateMorphTargets(){}dispose(){super.dispose(),this.morphTexture!==null&&(this.morphTexture.dispose(),this.morphTexture=null)}},Ss=new yn,xg=new ne(.5,.5),Lo=new R,br=class{constructor(e=new ei,t=new ei,n=new ei,i=new ei,r=new ei,a=new ei){this.planes=[e,t,n,i,r,a]}set(e,t,n,i,r,a){let o=this.planes;return o[0].copy(e),o[1].copy(t),o[2].copy(n),o[3].copy(i),o[4].copy(r),o[5].copy(a),this}copy(e){let t=this.planes;for(let n=0;n<6;n++)t[n].copy(e.planes[n]);return this}setFromProjectionMatrix(e,t=ni,n=!1){let i=this.planes,r=e.elements,a=r[0],o=r[1],c=r[2],l=r[3],h=r[4],u=r[5],d=r[6],p=r[7],g=r[8],v=r[9],f=r[10],m=r[11],_=r[12],b=r[13],x=r[14],T=r[15];if(i[0].setComponents(l-a,p-h,m-g,T-_).normalize(),i[1].setComponents(l+a,p+h,m+g,T+_).normalize(),i[2].setComponents(l+o,p+u,m+v,T+b).normalize(),i[3].setComponents(l-o,p-u,m-v,T-b).normalize(),n)i[4].setComponents(c,d,f,x).normalize(),i[5].setComponents(l-c,p-d,m-f,T-x).normalize();else if(i[4].setComponents(l-c,p-d,m-f,T-x).normalize(),t===ni)i[5].setComponents(l+c,p+d,m+f,T+x).normalize();else if(t===gr)i[5].setComponents(c,d,f,x).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+t);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),Ss.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{let t=e.geometry;t.boundingSphere===null&&t.computeBoundingSphere(),Ss.copy(t.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere(Ss)}intersectsSprite(e){Ss.center.set(0,0,0);let t=xg.distanceTo(e.center);return Ss.radius=.7071067811865476+t,Ss.applyMatrix4(e.matrixWorld),this.intersectsSphere(Ss)}intersectsSphere(e){let t=this.planes,n=e.center,i=-e.radius;for(let r=0;r<6;r++)if(t[r].distanceToPoint(n)<i)return!1;return!0}intersectsBox(e){let t=this.planes;for(let n=0;n<6;n++){let i=t[n];if(Lo.x=i.normal.x>0?e.max.x:e.min.x,Lo.y=i.normal.y>0?e.max.y:e.min.y,Lo.z=i.normal.z>0?e.max.z:e.min.z,i.distanceToPoint(Lo)<0)return!1}return!0}containsPoint(e){let t=this.planes;for(let n=0;n<6;n++)if(t[n].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}};var zn=class extends xn{constructor(e){super(),this.isLineBasicMaterial=!0,this.type="LineBasicMaterial",this.color=new Me(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.linewidth=e.linewidth,this.linecap=e.linecap,this.linejoin=e.linejoin,this.fog=e.fog,this}},il=new R,sl=new R,Kd=new je,ta=new Rs,No=new yn,gh=new R,Zd=new R,ii=class extends ft{constructor(e=new tt,t=new zn){super(),this.isLine=!0,this.type="Line",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}computeLineDistances(){let e=this.geometry;if(e.index===null){let t=e.attributes.position,n=[0];for(let i=1,r=t.count;i<r;i++)il.fromBufferAttribute(t,i-1),sl.fromBufferAttribute(t,i),n[i]=n[i-1],n[i]+=il.distanceTo(sl);e.setAttribute("lineDistance",new Oe(n,1))}else Le("Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}intersectsFrustum(e){return e.intersectsObject(this)}raycast(e,t){let n=this.geometry,i=this.matrixWorld,r=e.params.Line.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),No.copy(n.boundingSphere),No.applyMatrix4(i),No.radius+=r,e.ray.intersectsSphere(No)===!1)return;Kd.copy(i).invert(),ta.copy(e.ray).applyMatrix4(Kd);let o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=this.isLineSegments?2:1,h=n.index,d=n.attributes.position;if(h!==null){let p=Math.max(0,a.start),g=Math.min(h.count,a.start+a.count);for(let v=p,f=g-1;v<f;v+=l){let m=h.getX(v),_=h.getX(v+1),b=Do(this,e,ta,c,m,_,v);b&&t.push(b)}if(this.isLineLoop){let v=h.getX(g-1),f=h.getX(p),m=Do(this,e,ta,c,v,f,g-1);m&&t.push(m)}}else{let p=Math.max(0,a.start),g=Math.min(d.count,a.start+a.count);for(let v=p,f=g-1;v<f;v+=l){let m=Do(this,e,ta,c,v,v+1,v);m&&t.push(m)}if(this.isLineLoop){let v=Do(this,e,ta,c,g-1,p,g-1);v&&t.push(v)}}}updateMorphTargets(){let t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){let i=t[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=i.length;r<a;r++){let o=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}};function Do(s,e,t,n,i,r,a){let o=s.geometry.attributes.position;if(il.fromBufferAttribute(o,i),sl.fromBufferAttribute(o,r),t.distanceSqToSegment(il,sl,gh,Zd)>n)return;gh.applyMatrix4(s.matrixWorld);let l=e.ray.origin.distanceTo(gh);if(!(l<e.near||l>e.far))return{distance:l,point:Zd.clone().applyMatrix4(s.matrixWorld),index:a,face:null,faceIndex:null,barycoord:null,object:s}}var Jd=new R,$d=new R,Is=class extends ii{constructor(e,t){super(e,t),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){let e=this.geometry;if(e.index===null){let t=e.attributes.position,n=[];for(let i=0,r=t.count;i<r;i+=2)Jd.fromBufferAttribute(t,i),$d.fromBufferAttribute(t,i+1),n[i]=i===0?0:n[i-1],n[i+1]=n[i]+Jd.distanceTo($d);e.setAttribute("lineDistance",new Oe(n,1))}else Le("LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}},ma=class extends ii{constructor(e,t){super(e,t),this.isLineLoop=!0,this.type="LineLoop"}},Rn=class extends xn{constructor(e){super(),this.isPointsMaterial=!0,this.type="PointsMaterial",this.color=new Me(16777215),this.map=null,this.alphaMap=null,this.size=1,this.sizeAttenuation=!0,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.alphaMap=e.alphaMap,this.size=e.size,this.sizeAttenuation=e.sizeAttenuation,this.fog=e.fog,this}},jd=new je,Ch=new Rs,Uo=new yn,Fo=new R,Gn=class extends ft{constructor(e=new tt,t=new Rn){super(),this.isPoints=!0,this.type="Points",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}intersectsFrustum(e){return e.intersectsObject(this)}raycast(e,t){let n=this.geometry,i=this.matrixWorld,r=e.params.Points.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),Uo.copy(n.boundingSphere),Uo.applyMatrix4(i),Uo.radius+=r,e.ray.intersectsSphere(Uo)===!1)return;jd.copy(i).invert(),Ch.copy(e.ray).applyMatrix4(jd);let o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=n.index,u=n.attributes.position;if(l!==null){let d=Math.max(0,a.start),p=Math.min(l.count,a.start+a.count);for(let g=d,v=p;g<v;g++){let f=l.getX(g);Fo.fromBufferAttribute(u,f),Qd(Fo,f,c,i,e,t,this)}}else{let d=Math.max(0,a.start),p=Math.min(u.count,a.start+a.count);for(let g=d,v=p;g<v;g++)Fo.fromBufferAttribute(u,g),Qd(Fo,g,c,i,e,t,this)}}updateMorphTargets(){let t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){let i=t[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=i.length;r<a;r++){let o=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}};function Qd(s,e,t,n,i,r,a){let o=Ch.distanceSqToPoint(s);if(o<t){let c=new R;Ch.closestPointToPoint(s,c),c.applyMatrix4(n);let l=i.ray.origin.distanceTo(c);if(l<i.near||l>i.far)return;r.push({distance:l,distanceToRay:Math.sqrt(o),point:c,index:e,face:null,faceIndex:null,barycoord:null,object:a})}}var ga=class extends jt{constructor(e=[],t=us,n,i,r,a,o,c,l,h){super(e,t,n,i,r,a,o,c,l,h),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}},Mi=class extends jt{constructor(e,t,n,i,r,a,o,c,l){super(e,t,n,i,r,a,o,c,l),this.isCanvasTexture=!0,this.needsUpdate=!0}};var as=class extends jt{constructor(e,t,n=oi,i,r,a,o=Wt,c=Wt,l,h=yi,u=1){if(h!==yi&&h!==ds)throw new Error("THREE.DepthTexture: format must be either THREE.DepthFormat or THREE.DepthStencilFormat");let d={width:e,height:t,depth:u};super(d,i,r,a,o,c,h,n,l),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.source=new yr(Object.assign({},e.image)),this.compareFunction=e.compareFunction,this}toJSON(e){let t=super.toJSON(e);return t.compareFunction=this.compareFunction,t}},rl=class extends as{constructor(e,t=oi,n=us,i,r,a=Wt,o=Wt,c,l=yi){let h={width:e,height:e,depth:1},u=[h,h,h,h,h,h];super(e,e,t,n,i,r,a,o,c,l),this.image=u,this.isCubeDepthTexture=!0,this.isCubeTexture=!0}get images(){return this.image}set images(e){this.image=e}},xa=class extends jt{constructor(e=null){super(),this.sourceTexture=e,this.isExternalTexture=!0}copy(e){return super.copy(e),this.sourceTexture=e.sourceTexture,this}},Mn=class s extends tt{constructor(e=1,t=1,n=1,i=1,r=1,a=1){super(),this.type="BoxGeometry",this.parameters={width:e,height:t,depth:n,widthSegments:i,heightSegments:r,depthSegments:a};let o=this;i=Math.floor(i),r=Math.floor(r),a=Math.floor(a);let c=[],l=[],h=[],u=[],d=0,p=0;g("z","y","x",-1,-1,n,t,e,a,r,0),g("z","y","x",1,-1,n,t,-e,a,r,1),g("x","z","y",1,1,e,n,t,i,a,2),g("x","z","y",1,-1,e,n,-t,i,a,3),g("x","y","z",1,-1,e,t,n,i,r,4),g("x","y","z",-1,-1,e,t,-n,i,r,5),this.setIndex(c),this.setAttribute("position",new Oe(l,3)),this.setAttribute("normal",new Oe(h,3)),this.setAttribute("uv",new Oe(u,2));function g(v,f,m,_,b,x,T,S,A,y,E){let I=x/A,L=T/y,F=x/2,V=T/2,D=S/2,B=A+1,X=y+1,W=0,re=0,q=new R;for(let j=0;j<X;j++){let te=j*L-V;for(let Ne=0;Ne<B;Ne++){let Ae=Ne*I-F;q[v]=Ae*_,q[f]=te*b,q[m]=D,l.push(q.x,q.y,q.z),q[v]=0,q[f]=0,q[m]=S>0?1:-1,h.push(q.x,q.y,q.z),u.push(Ne/A),u.push(1-j/y),W+=1}}for(let j=0;j<y;j++)for(let te=0;te<A;te++){let Ne=d+te+B*j,Ae=d+te+B*(j+1),vt=d+(te+1)+B*(j+1),ct=d+(te+1)+B*j;c.push(Ne,Ae,ct),c.push(Ae,vt,ct),re+=6}o.addGroup(p,re,E),p+=re,d+=W}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.width,e.height,e.depth,e.widthSegments,e.heightSegments,e.depthSegments)}};var _a=class s extends tt{constructor(e=1,t=32,n=0,i=Math.PI*2){super(),this.type="CircleGeometry",this.parameters={radius:e,segments:t,thetaStart:n,thetaLength:i},t=Math.max(3,t);let r=[],a=[],o=[],c=[],l=new R,h=new ne;a.push(0,0,0),o.push(0,0,1),c.push(.5,.5);for(let u=0,d=3;u<=t;u++,d+=3){let p=n+u/t*i;l.x=e*Math.cos(p),l.y=e*Math.sin(p),a.push(l.x,l.y,l.z),o.push(0,0,1),h.x=(a[d]/e+1)/2,h.y=(a[d+1]/e+1)/2,c.push(h.x,h.y)}for(let u=1;u<=t;u++)r.push(u,u+1,0);this.setIndex(r),this.setAttribute("position",new Oe(a,3)),this.setAttribute("normal",new Oe(o,3)),this.setAttribute("uv",new Oe(c,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.radius,e.segments,e.thetaStart,e.thetaLength)}},_n=class s extends tt{constructor(e=1,t=1,n=1,i=32,r=1,a=!1,o=0,c=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop:e,radiusBottom:t,height:n,radialSegments:i,heightSegments:r,openEnded:a,thetaStart:o,thetaLength:c};let l=this;i=Math.floor(i),r=Math.floor(r);let h=[],u=[],d=[],p=[],g=0,v=[],f=n/2,m=0;_(),a===!1&&(e>0&&b(!0),t>0&&b(!1)),this.setIndex(h),this.setAttribute("position",new Oe(u,3)),this.setAttribute("normal",new Oe(d,3)),this.setAttribute("uv",new Oe(p,2));function _(){let x=new R,T=new R,S=0,A=(t-e)/n;for(let y=0;y<=r;y++){let E=[],I=y/r,L=I*(t-e)+e;for(let F=0;F<=i;F++){let V=F/i,D=V*c+o,B=Math.sin(D),X=Math.cos(D);T.x=L*B,T.y=-I*n+f,T.z=L*X,u.push(T.x,T.y,T.z),x.set(B,A,X).normalize(),d.push(x.x,x.y,x.z),p.push(V,1-I),E.push(g++)}v.push(E)}for(let y=0;y<i;y++)for(let E=0;E<r;E++){let I=v[E][y],L=v[E+1][y],F=v[E+1][y+1],V=v[E][y+1];(e>0||E!==0)&&(h.push(I,L,V),S+=3),(t>0||E!==r-1)&&(h.push(L,F,V),S+=3)}l.addGroup(m,S,0),m+=S}function b(x){let T=g,S=new ne,A=new R,y=0,E=x===!0?e:t,I=x===!0?1:-1;for(let F=1;F<=i;F++)u.push(0,f*I,0),d.push(0,I,0),p.push(.5,.5),g++;let L=g;for(let F=0;F<=i;F++){let D=F/i*c+o,B=Math.cos(D),X=Math.sin(D);A.x=E*X,A.y=f*I,A.z=E*B,u.push(A.x,A.y,A.z),d.push(0,I,0),S.x=B*.5+.5,S.y=X*.5*I+.5,p.push(S.x,S.y),g++}for(let F=0;F<i;F++){let V=T+F,D=L+F;x===!0?h.push(D,D+1,V):h.push(D+1,D,V),y+=3}l.addGroup(m,y,x===!0?1:2),m+=y}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.radiusTop,e.radiusBottom,e.height,e.radialSegments,e.heightSegments,e.openEnded,e.thetaStart,e.thetaLength)}},os=class s extends _n{constructor(e=1,t=1,n=32,i=1,r=!1,a=0,o=Math.PI*2){super(0,e,t,n,i,r,a,o),this.type="ConeGeometry",this.parameters={radius:e,height:t,radialSegments:n,heightSegments:i,openEnded:r,thetaStart:a,thetaLength:o}}static fromJSON(e){return new s(e.radius,e.height,e.radialSegments,e.heightSegments,e.openEnded,e.thetaStart,e.thetaLength)}},ya=class s extends tt{constructor(e=[],t=[],n=1,i=0){super(),this.type="PolyhedronGeometry",this.parameters={vertices:e,indices:t,radius:n,detail:i};let r=[],a=[];o(i),l(n),h(),this.setAttribute("position",new Oe(r,3)),this.setAttribute("normal",new Oe(r.slice(),3)),this.setAttribute("uv",new Oe(a,2)),i===0?this.computeVertexNormals():this.normalizeNormals();function o(_){let b=new R,x=new R,T=new R;for(let S=0;S<t.length;S+=3)p(t[S+0],b),p(t[S+1],x),p(t[S+2],T),c(b,x,T,_)}function c(_,b,x,T){let S=T+1,A=[];for(let y=0;y<=S;y++){A[y]=[];let E=_.clone().lerp(x,y/S),I=b.clone().lerp(x,y/S),L=S-y;for(let F=0;F<=L;F++)F===0&&y===S?A[y][F]=E:A[y][F]=E.clone().lerp(I,F/L)}for(let y=0;y<S;y++)for(let E=0;E<2*(S-y)-1;E++){let I=Math.floor(E/2);E%2===0?(d(A[y][I+1]),d(A[y+1][I]),d(A[y][I])):(d(A[y][I+1]),d(A[y+1][I+1]),d(A[y+1][I]))}}function l(_){let b=new R;for(let x=0;x<r.length;x+=3)b.x=r[x+0],b.y=r[x+1],b.z=r[x+2],b.normalize().multiplyScalar(_),r[x+0]=b.x,r[x+1]=b.y,r[x+2]=b.z}function h(){let _=new R;for(let b=0;b<r.length;b+=3){_.x=r[b+0],_.y=r[b+1],_.z=r[b+2];let x=f(_)/2/Math.PI+.5,T=m(_)/Math.PI+.5;a.push(x,1-T)}g(),u()}function u(){for(let _=0;_<a.length;_+=6){let b=a[_+0],x=a[_+2],T=a[_+4],S=Math.max(b,x,T),A=Math.min(b,x,T);S>.9&&A<.1&&(b<.2&&(a[_+0]+=1),x<.2&&(a[_+2]+=1),T<.2&&(a[_+4]+=1))}}function d(_){r.push(_.x,_.y,_.z)}function p(_,b){let x=_*3;b.x=e[x+0],b.y=e[x+1],b.z=e[x+2]}function g(){let _=new R,b=new R,x=new R,T=new R,S=new ne,A=new ne,y=new ne;for(let E=0,I=0;E<r.length;E+=9,I+=6){_.set(r[E+0],r[E+1],r[E+2]),b.set(r[E+3],r[E+4],r[E+5]),x.set(r[E+6],r[E+7],r[E+8]),S.set(a[I+0],a[I+1]),A.set(a[I+2],a[I+3]),y.set(a[I+4],a[I+5]),T.copy(_).add(b).add(x).divideScalar(3);let L=f(T);v(S,I+0,_,L),v(A,I+2,b,L),v(y,I+4,x,L)}}function v(_,b,x,T){T<0&&_.x===1&&(a[b]=_.x-1),x.x===0&&x.z===0&&(a[b]=T/2/Math.PI+.5)}function f(_){return Math.atan2(_.z,-_.x)}function m(_){return Math.atan2(-_.y,Math.sqrt(_.x*_.x+_.z*_.z))}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.vertices,e.indices,e.radius,e.detail)}};var Oo=new R,Bo=new R,xh=new R,ko=new mi,va=class extends tt{constructor(e=null,t=1){if(super(),this.type="EdgesGeometry",this.parameters={geometry:e,thresholdAngle:t},e!==null){let i=Math.pow(10,4),r=Math.cos(dr*t),a=e.getIndex(),o=e.getAttribute("position"),c=a?a.count:o.count,l=[0,0,0],h=["a","b","c"],u=new Array(3),d={},p=[];for(let g=0;g<c;g+=3){a?(l[0]=a.getX(g),l[1]=a.getX(g+1),l[2]=a.getX(g+2)):(l[0]=g,l[1]=g+1,l[2]=g+2);let{a:v,b:f,c:m}=ko;if(v.fromBufferAttribute(o,l[0]),f.fromBufferAttribute(o,l[1]),m.fromBufferAttribute(o,l[2]),ko.getNormal(xh),u[0]=`${Math.round(v.x*i)},${Math.round(v.y*i)},${Math.round(v.z*i)}`,u[1]=`${Math.round(f.x*i)},${Math.round(f.y*i)},${Math.round(f.z*i)}`,u[2]=`${Math.round(m.x*i)},${Math.round(m.y*i)},${Math.round(m.z*i)}`,!(u[0]===u[1]||u[1]===u[2]||u[2]===u[0]))for(let _=0;_<3;_++){let b=(_+1)%3,x=u[_],T=u[b],S=ko[h[_]],A=ko[h[b]],y=`${x}_${T}`,E=`${T}_${x}`;E in d&&d[E]?(xh.dot(d[E].normal)<=r&&(p.push(S.x,S.y,S.z),p.push(A.x,A.y,A.z)),d[E]=null):y in d||(d[y]={index0:l[_],index1:l[b],normal:xh.clone()})}}for(let g in d)if(d[g]){let{index0:v,index1:f}=d[g];Oo.fromBufferAttribute(o,v),Bo.fromBufferAttribute(o,f),p.push(Oo.x,Oo.y,Oo.z),p.push(Bo.x,Bo.y,Bo.z)}this.setAttribute("position",new Oe(p,3))}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}},In=class{constructor(){this.type="Curve",this.arcLengthDivisions=200,this.needsUpdate=!1,this.cacheArcLengths=null}getPoint(){Le("Curve: .getPoint() not implemented.")}getPointAt(e,t){let n=this.getUtoTmapping(e);return this.getPoint(n,t)}getPoints(e=5){let t=[];for(let n=0;n<=e;n++)t.push(this.getPoint(n/e));return t}getSpacedPoints(e=5){let t=[];for(let n=0;n<=e;n++)t.push(this.getPointAt(n/e));return t}getLength(){let e=this.getLengths();return e[e.length-1]}getLengths(e=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===e+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;let t=[],n,i=this.getPoint(0),r=0;t.push(0);for(let a=1;a<=e;a++)n=this.getPoint(a/e),r+=n.distanceTo(i),t.push(r),i=n;return this.cacheArcLengths=t,t}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(e,t=null){let n=this.getLengths(),i=0,r=n.length,a;t?a=t:a=e*n[r-1];let o=0,c=r-1,l;for(;o<=c;)if(i=Math.floor(o+(c-o)/2),l=n[i]-a,l<0)o=i+1;else if(l>0)c=i-1;else{c=i;break}if(i=c,n[i]===a)return i/(r-1);let h=n[i],d=n[i+1]-h,p=(a-h)/d;return(i+p)/(r-1)}getTangent(e,t){let i=e-1e-4,r=e+1e-4;i<0&&(i=0),r>1&&(r=1);let a=this.getPoint(i),o=this.getPoint(r),c=t||(a.isVector2?new ne:new R);return c.copy(o).sub(a).normalize(),c}getTangentAt(e,t){let n=this.getUtoTmapping(e);return this.getTangent(n,t)}computeFrenetFrames(e,t=!1){let n=new R,i=[],r=[],a=[],o=new R,c=new je;for(let p=0;p<=e;p++){let g=p/e;i[p]=this.getTangentAt(g,new R)}r[0]=new R,a[0]=new R;let l=Number.MAX_VALUE,h=Math.abs(i[0].x),u=Math.abs(i[0].y),d=Math.abs(i[0].z);h<=l&&(l=h,n.set(1,0,0)),u<=l&&(l=u,n.set(0,1,0)),d<=l&&n.set(0,0,1),o.crossVectors(i[0],n).normalize(),r[0].crossVectors(i[0],o),a[0].crossVectors(i[0],r[0]);for(let p=1;p<=e;p++){if(r[p]=r[p-1].clone(),a[p]=a[p-1].clone(),o.crossVectors(i[p-1],i[p]),o.length()>Number.EPSILON){o.normalize();let g=Math.acos(ot(i[p-1].dot(i[p]),-1,1));r[p].applyMatrix4(c.makeRotationAxis(o,g))}a[p].crossVectors(i[p],r[p])}if(t===!0){let p=Math.acos(ot(r[0].dot(r[e]),-1,1));p/=e,i[0].dot(o.crossVectors(r[0],r[e]))>0&&(p=-p);for(let g=1;g<=e;g++)r[g].applyMatrix4(c.makeRotationAxis(i[g],p*g)),a[g].crossVectors(i[g],r[g])}return{tangents:i,normals:r,binormals:a}}clone(){return new this.constructor().copy(this)}copy(e){return this.arcLengthDivisions=e.arcLengthDivisions,this}toJSON(){let e={metadata:{version:4.7,type:"Curve",generator:"Curve.toJSON"}};return e.arcLengthDivisions=this.arcLengthDivisions,e.type=this.type,e}fromJSON(e){return this.arcLengthDivisions=e.arcLengthDivisions,this}},Tr=class extends In{constructor(e=0,t=0,n=1,i=1,r=0,a=Math.PI*2,o=!1,c=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=e,this.aY=t,this.xRadius=n,this.yRadius=i,this.aStartAngle=r,this.aEndAngle=a,this.aClockwise=o,this.aRotation=c}getPoint(e,t=new ne){let n=t,i=Math.PI*2,r=this.aEndAngle-this.aStartAngle,a=Math.abs(r)<Number.EPSILON;for(;r<0;)r+=i;for(;r>i;)r-=i;r<Number.EPSILON&&(a?r=0:r=i),this.aClockwise===!0&&!a&&(r===i?r=-i:r=r-i);let o=this.aStartAngle+e*r,c=this.aX+this.xRadius*Math.cos(o),l=this.aY+this.yRadius*Math.sin(o);if(this.aRotation!==0){let h=Math.cos(this.aRotation),u=Math.sin(this.aRotation),d=c-this.aX,p=l-this.aY;c=d*h-p*u+this.aX,l=d*u+p*h+this.aY}return n.set(c,l)}copy(e){return super.copy(e),this.aX=e.aX,this.aY=e.aY,this.xRadius=e.xRadius,this.yRadius=e.yRadius,this.aStartAngle=e.aStartAngle,this.aEndAngle=e.aEndAngle,this.aClockwise=e.aClockwise,this.aRotation=e.aRotation,this}toJSON(){let e=super.toJSON();return e.aX=this.aX,e.aY=this.aY,e.xRadius=this.xRadius,e.yRadius=this.yRadius,e.aStartAngle=this.aStartAngle,e.aEndAngle=this.aEndAngle,e.aClockwise=this.aClockwise,e.aRotation=this.aRotation,e}fromJSON(e){return super.fromJSON(e),this.aX=e.aX,this.aY=e.aY,this.xRadius=e.xRadius,this.yRadius=e.yRadius,this.aStartAngle=e.aStartAngle,this.aEndAngle=e.aEndAngle,this.aClockwise=e.aClockwise,this.aRotation=e.aRotation,this}},al=class extends Tr{constructor(e,t,n,i,r,a){super(e,t,n,n,i,r,a),this.isArcCurve=!0,this.type="ArcCurve"}};function nu(){let s=0,e=0,t=0,n=0;function i(r,a,o,c){s=r,e=o,t=-3*r+3*a-2*o-c,n=2*r-2*a+o+c}return{initCatmullRom:function(r,a,o,c,l){i(a,o,l*(o-r),l*(c-a))},initNonuniformCatmullRom:function(r,a,o,c,l,h,u){let d=(a-r)/l-(o-r)/(l+h)+(o-a)/h,p=(o-a)/h-(c-a)/(h+u)+(c-o)/u;d*=h,p*=h,i(a,o,d,p)},calc:function(r){let a=r*r,o=a*r;return s+e*r+t*a+n*o}}}var ef=new R,tf=new R,_h=new nu,yh=new nu,vh=new nu,Pn=class extends In{constructor(e=[],t=!1,n="centripetal",i=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=e,this.closed=t,this.curveType=n,this.tension=i}getPoint(e,t=new R){let n=t,i=this.points,r=i.length,a=(r-(this.closed?0:1))*e,o=Math.floor(a),c=a-o;this.closed?o+=o>0?0:(Math.floor(Math.abs(o)/r)+1)*r:c===0&&o===r-1&&(o=r-2,c=1);let l,h;this.closed||o>0?l=i[(o-1)%r]:(tf.subVectors(i[0],i[1]).add(i[0]),l=tf);let u=i[o%r],d=i[(o+1)%r];if(this.closed||o+2<r?h=i[(o+2)%r]:(ef.subVectors(i[r-1],i[r-2]).add(i[r-1]),h=ef),this.curveType==="centripetal"||this.curveType==="chordal"){let p=this.curveType==="chordal"?.5:.25,g=Math.pow(l.distanceToSquared(u),p),v=Math.pow(u.distanceToSquared(d),p),f=Math.pow(d.distanceToSquared(h),p);v<1e-4&&(v=1),g<1e-4&&(g=v),f<1e-4&&(f=v),_h.initNonuniformCatmullRom(l.x,u.x,d.x,h.x,g,v,f),yh.initNonuniformCatmullRom(l.y,u.y,d.y,h.y,g,v,f),vh.initNonuniformCatmullRom(l.z,u.z,d.z,h.z,g,v,f)}else this.curveType==="catmullrom"&&(_h.initCatmullRom(l.x,u.x,d.x,h.x,this.tension),yh.initCatmullRom(l.y,u.y,d.y,h.y,this.tension),vh.initCatmullRom(l.z,u.z,d.z,h.z,this.tension));return n.set(_h.calc(c),yh.calc(c),vh.calc(c)),n}copy(e){super.copy(e),this.points=[];for(let t=0,n=e.points.length;t<n;t++){let i=e.points[t];this.points.push(i.clone())}return this.closed=e.closed,this.curveType=e.curveType,this.tension=e.tension,this}toJSON(){let e=super.toJSON();e.points=[];for(let t=0,n=this.points.length;t<n;t++){let i=this.points[t];e.points.push(i.toArray())}return e.closed=this.closed,e.curveType=this.curveType,e.tension=this.tension,e}fromJSON(e){super.fromJSON(e),this.points=[];for(let t=0,n=e.points.length;t<n;t++){let i=e.points[t];this.points.push(new R().fromArray(i))}return this.closed=e.closed,this.curveType=e.curveType,this.tension=e.tension,this}};function nf(s,e,t,n,i){let r=(n-e)*.5,a=(i-t)*.5,o=s*s,c=s*o;return(2*t-2*n+r+a)*c+(-3*t+3*n-2*r-a)*o+r*s+t}function _g(s,e){let t=1-s;return t*t*e}function yg(s,e){return 2*(1-s)*s*e}function vg(s,e){return s*s*e}function sa(s,e,t,n){return _g(s,e)+yg(s,t)+vg(s,n)}function Mg(s,e){let t=1-s;return t*t*t*e}function Sg(s,e){let t=1-s;return 3*t*t*s*e}function bg(s,e){return 3*(1-s)*s*s*e}function Tg(s,e){return s*s*s*e}function ra(s,e,t,n,i){return Mg(s,e)+Sg(s,t)+bg(s,n)+Tg(s,i)}var Ma=class extends In{constructor(e=new ne,t=new ne,n=new ne,i=new ne){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=e,this.v1=t,this.v2=n,this.v3=i}getPoint(e,t=new ne){let n=t,i=this.v0,r=this.v1,a=this.v2,o=this.v3;return n.set(ra(e,i.x,r.x,a.x,o.x),ra(e,i.y,r.y,a.y,o.y)),n}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this.v3.copy(e.v3),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e.v3=this.v3.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this.v3.fromArray(e.v3),this}},ol=class extends In{constructor(e=new R,t=new R,n=new R,i=new R){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=e,this.v1=t,this.v2=n,this.v3=i}getPoint(e,t=new R){let n=t,i=this.v0,r=this.v1,a=this.v2,o=this.v3;return n.set(ra(e,i.x,r.x,a.x,o.x),ra(e,i.y,r.y,a.y,o.y),ra(e,i.z,r.z,a.z,o.z)),n}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this.v3.copy(e.v3),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e.v3=this.v3.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this.v3.fromArray(e.v3),this}},Sa=class extends In{constructor(e=new ne,t=new ne){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=e,this.v2=t}getPoint(e,t=new ne){let n=t;return e===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(e).add(this.v1)),n}getPointAt(e,t){return this.getPoint(e,t)}getTangent(e,t=new ne){return t.subVectors(this.v2,this.v1).normalize()}getTangentAt(e,t){return this.getTangent(e,t)}copy(e){return super.copy(e),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},ll=class extends In{constructor(e=new R,t=new R){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=e,this.v2=t}getPoint(e,t=new R){let n=t;return e===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(e).add(this.v1)),n}getPointAt(e,t){return this.getPoint(e,t)}getTangent(e,t=new R){return t.subVectors(this.v2,this.v1).normalize()}getTangentAt(e,t){return this.getTangent(e,t)}copy(e){return super.copy(e),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},ba=class extends In{constructor(e=new ne,t=new ne,n=new ne){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=e,this.v1=t,this.v2=n}getPoint(e,t=new ne){let n=t,i=this.v0,r=this.v1,a=this.v2;return n.set(sa(e,i.x,r.x,a.x),sa(e,i.y,r.y,a.y)),n}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},Ta=class extends In{constructor(e=new R,t=new R,n=new R){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=e,this.v1=t,this.v2=n}getPoint(e,t=new R){let n=t,i=this.v0,r=this.v1,a=this.v2;return n.set(sa(e,i.x,r.x,a.x),sa(e,i.y,r.y,a.y),sa(e,i.z,r.z,a.z)),n}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},wa=class extends In{constructor(e=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=e}getPoint(e,t=new ne){let n=t,i=this.points,r=(i.length-1)*e,a=Math.floor(r),o=r-a,c=i[a===0?a:a-1],l=i[a],h=i[a>i.length-2?i.length-1:a+1],u=i[a>i.length-3?i.length-1:a+2];return n.set(nf(o,c.x,l.x,h.x,u.x),nf(o,c.y,l.y,h.y,u.y)),n}copy(e){super.copy(e),this.points=[];for(let t=0,n=e.points.length;t<n;t++){let i=e.points[t];this.points.push(i.clone())}return this}toJSON(){let e=super.toJSON();e.points=[];for(let t=0,n=this.points.length;t<n;t++){let i=this.points[t];e.points.push(i.toArray())}return e}fromJSON(e){super.fromJSON(e),this.points=[];for(let t=0,n=e.points.length;t<n;t++){let i=e.points[t];this.points.push(new ne().fromArray(i))}return this}},cl=Object.freeze({__proto__:null,ArcCurve:al,CatmullRomCurve3:Pn,CubicBezierCurve:Ma,CubicBezierCurve3:ol,EllipseCurve:Tr,LineCurve:Sa,LineCurve3:ll,QuadraticBezierCurve:ba,QuadraticBezierCurve3:Ta,SplineCurve:wa}),hl=class extends In{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(e){this.curves.push(e)}closePath(){let e=this.curves[0].getPoint(0),t=this.curves[this.curves.length-1].getPoint(1);if(!e.equals(t)){let n=e.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new cl[n](t,e))}return this}getPoint(e,t){let n=e*this.getLength(),i=this.getCurveLengths(),r=0;for(;r<i.length;){if(i[r]>=n){let a=i[r]-n,o=this.curves[r],c=o.getLength(),l=c===0?0:1-a/c;return o.getPointAt(l,t)}r++}return null}getLength(){let e=this.getCurveLengths();return e[e.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;let e=[],t=0;for(let n=0,i=this.curves.length;n<i;n++)t+=this.curves[n].getLength(),e.push(t);return this.cacheLengths=e,e}getSpacedPoints(e=40){let t=[];for(let n=0;n<=e;n++)t.push(this.getPoint(n/e));return this.autoClose&&t.push(t[0]),t}getPoints(e=12){let t=[],n;for(let i=0,r=this.curves;i<r.length;i++){let a=r[i],o=a.isEllipseCurve?e*2:a.isLineCurve||a.isLineCurve3?1:a.isSplineCurve?e*a.points.length:e,c=a.getPoints(o);for(let l=0;l<c.length;l++){let h=c[l];n&&n.equals(h)||(t.push(h),n=h)}}return this.autoClose&&t.length>1&&!t[t.length-1].equals(t[0])&&t.push(t[0]),t}copy(e){super.copy(e),this.curves=[];for(let t=0,n=e.curves.length;t<n;t++){let i=e.curves[t];this.curves.push(i.clone())}return this.autoClose=e.autoClose,this}toJSON(){let e=super.toJSON();e.autoClose=this.autoClose,e.curves=[];for(let t=0,n=this.curves.length;t<n;t++){let i=this.curves[t];e.curves.push(i.toJSON())}return e}fromJSON(e){super.fromJSON(e),this.autoClose=e.autoClose,this.curves=[];for(let t=0,n=e.curves.length;t<n;t++){let i=e.curves[t];this.curves.push(new cl[i.type]().fromJSON(i))}return this}},Aa=class extends hl{constructor(e){super(),this.type="Path",this.currentPoint=new ne,e&&this.setFromPoints(e)}setFromPoints(e){this.moveTo(e[0].x,e[0].y);for(let t=1,n=e.length;t<n;t++)this.lineTo(e[t].x,e[t].y);return this}moveTo(e,t){return this.currentPoint.set(e,t),this}lineTo(e,t){let n=new Sa(this.currentPoint.clone(),new ne(e,t));return this.curves.push(n),this.currentPoint.set(e,t),this}quadraticCurveTo(e,t,n,i){let r=new ba(this.currentPoint.clone(),new ne(e,t),new ne(n,i));return this.curves.push(r),this.currentPoint.set(n,i),this}bezierCurveTo(e,t,n,i,r,a){let o=new Ma(this.currentPoint.clone(),new ne(e,t),new ne(n,i),new ne(r,a));return this.curves.push(o),this.currentPoint.set(r,a),this}splineThru(e){let t=[this.currentPoint.clone()].concat(e),n=new wa(t);return this.curves.push(n),this.currentPoint.copy(e[e.length-1]),this}arc(e,t,n,i,r,a){let o=this.currentPoint.x,c=this.currentPoint.y;return this.absarc(e+o,t+c,n,i,r,a),this}absarc(e,t,n,i,r,a){return this.absellipse(e,t,n,n,i,r,a),this}ellipse(e,t,n,i,r,a,o,c){let l=this.currentPoint.x,h=this.currentPoint.y;return this.absellipse(e+l,t+h,n,i,r,a,o,c),this}absellipse(e,t,n,i,r,a,o,c){let l=new Tr(e,t,n,i,r,a,o,c);if(this.curves.length>0){let u=l.getPoint(0);u.equals(this.currentPoint)||this.lineTo(u.x,u.y)}this.curves.push(l);let h=l.getPoint(1);return this.currentPoint.copy(h),this}copy(e){return super.copy(e),this.currentPoint.copy(e.currentPoint),this}toJSON(){let e=super.toJSON();return e.currentPoint=this.currentPoint.toArray(),e}fromJSON(e){return super.fromJSON(e),this.currentPoint.fromArray(e.currentPoint),this}},Vn=class extends Aa{constructor(e){super(e),this.uuid=kn(),this.type="Shape",this.holes=[]}getPointsHoles(e){let t=[];for(let n=0,i=this.holes.length;n<i;n++)t[n]=this.holes[n].getPoints(e);return t}extractPoints(e){return{shape:this.getPoints(e),holes:this.getPointsHoles(e)}}copy(e){super.copy(e),this.holes=[];for(let t=0,n=e.holes.length;t<n;t++){let i=e.holes[t];this.holes.push(i.clone())}return this}toJSON(){let e=super.toJSON();e.uuid=this.uuid,e.holes=[];for(let t=0,n=this.holes.length;t<n;t++){let i=this.holes[t];e.holes.push(i.toJSON())}return e}fromJSON(e){super.fromJSON(e),this.uuid=e.uuid,this.holes=[];for(let t=0,n=e.holes.length;t<n;t++){let i=e.holes[t];this.holes.push(new Aa().fromJSON(i))}return this}};function wg(s,e,t=2){let n=e&&e.length,i=n?e[0]*t:s.length,r=tp(s,0,i,t,!0),a=[];if(!r||r.next===r.prev)return a;let o,c,l;if(n&&(r=Ig(s,e,r,t)),s.length>80*t){o=s[0],c=s[1];let h=o,u=c;for(let d=t;d<i;d+=t){let p=s[d],g=s[d+1];p<o&&(o=p),g<c&&(c=g),p>h&&(h=p),g>u&&(u=g)}l=Math.max(h-o,u-c),l=l!==0?32767/l:0}return Ea(r,a,t,o,c,l,0),a}function tp(s,e,t,n,i){let r;if(i===Gg(s,e,t,n)>0)for(let a=e;a<t;a+=n)r=sf(a/n|0,s[a],s[a+1],r);else for(let a=t-n;a>=e;a-=n)r=sf(a/n|0,s[a],s[a+1],r);return r&&wr(r,r.next)&&(Ra(r),r=r.next),r}function Ps(s,e){if(!s)return s;e||(e=s);let t=s,n;do if(n=!1,!t.steiner&&(wr(t,t.next)||Gt(t.prev,t,t.next)===0)){if(Ra(t),t=e=t.prev,t===t.next)break;n=!0}else t=t.next;while(n||t!==e);return e}function Ea(s,e,t,n,i,r,a){if(!s)return;!a&&r&&Ug(s,n,i,r);let o=s;for(;s.prev!==s.next;){let c=s.prev,l=s.next;if(r?Eg(s,n,i,r):Ag(s)){e.push(c.i,s.i,l.i),Ra(s),s=l.next,o=l.next;continue}if(s=l,s===o){a?a===1?(s=Cg(Ps(s),e),Ea(s,e,t,n,i,r,2)):a===2&&Rg(s,e,t,n,i,r):Ea(Ps(s),e,t,n,i,r,1);break}}}function Ag(s){let e=s.prev,t=s,n=s.next;if(Gt(e,t,n)>=0)return!1;let i=e.x,r=t.x,a=n.x,o=e.y,c=t.y,l=n.y,h=Math.min(i,r,a),u=Math.min(o,c,l),d=Math.max(i,r,a),p=Math.max(o,c,l),g=n.next;for(;g!==e;){if(g.x>=h&&g.x<=d&&g.y>=u&&g.y<=p&&na(i,o,r,c,a,l,g.x,g.y)&&Gt(g.prev,g,g.next)>=0)return!1;g=g.next}return!0}function Eg(s,e,t,n){let i=s.prev,r=s,a=s.next;if(Gt(i,r,a)>=0)return!1;let o=i.x,c=r.x,l=a.x,h=i.y,u=r.y,d=a.y,p=Math.min(o,c,l),g=Math.min(h,u,d),v=Math.max(o,c,l),f=Math.max(h,u,d),m=Rh(p,g,e,t,n),_=Rh(v,f,e,t,n),b=s.prevZ,x=s.nextZ;for(;b&&b.z>=m&&x&&x.z<=_;){if(b.x>=p&&b.x<=v&&b.y>=g&&b.y<=f&&b!==i&&b!==a&&na(o,h,c,u,l,d,b.x,b.y)&&Gt(b.prev,b,b.next)>=0||(b=b.prevZ,x.x>=p&&x.x<=v&&x.y>=g&&x.y<=f&&x!==i&&x!==a&&na(o,h,c,u,l,d,x.x,x.y)&&Gt(x.prev,x,x.next)>=0))return!1;x=x.nextZ}for(;b&&b.z>=m;){if(b.x>=p&&b.x<=v&&b.y>=g&&b.y<=f&&b!==i&&b!==a&&na(o,h,c,u,l,d,b.x,b.y)&&Gt(b.prev,b,b.next)>=0)return!1;b=b.prevZ}for(;x&&x.z<=_;){if(x.x>=p&&x.x<=v&&x.y>=g&&x.y<=f&&x!==i&&x!==a&&na(o,h,c,u,l,d,x.x,x.y)&&Gt(x.prev,x,x.next)>=0)return!1;x=x.nextZ}return!0}function Cg(s,e){let t=s;do{let n=t.prev,i=t.next.next;!wr(n,i)&&ip(n,t,t.next,i)&&Ca(n,i)&&Ca(i,n)&&(e.push(n.i,t.i,i.i),Ra(t),Ra(t.next),t=s=i),t=t.next}while(t!==s);return Ps(t)}function Rg(s,e,t,n,i,r){let a=s;do{let o=a.next.next;for(;o!==a.prev;){if(a.i!==o.i&&Bg(a,o)){let c=sp(a,o);a=Ps(a,a.next),c=Ps(c,c.next),Ea(a,e,t,n,i,r,0),Ea(c,e,t,n,i,r,0);return}o=o.next}a=a.next}while(a!==s)}function Ig(s,e,t,n){let i=[];for(let r=0,a=e.length;r<a;r++){let o=e[r]*n,c=r<a-1?e[r+1]*n:s.length,l=tp(s,o,c,n,!1);l===l.next&&(l.steiner=!0),i.push(Og(l))}i.sort(Pg);for(let r=0;r<i.length;r++)t=Lg(i[r],t);return t}function Pg(s,e){let t=s.x-e.x;if(t===0&&(t=s.y-e.y,t===0)){let n=(s.next.y-s.y)/(s.next.x-s.x),i=(e.next.y-e.y)/(e.next.x-e.x);t=n-i}return t}function Lg(s,e){let t=Ng(s,e);if(!t)return e;let n=sp(t,s);return Ps(n,n.next),Ps(t,t.next)}function Ng(s,e){let t=e,n=s.x,i=s.y,r=-1/0,a;if(wr(s,t))return t;do{if(wr(s,t.next))return t.next;if(i<=t.y&&i>=t.next.y&&t.next.y!==t.y){let u=t.x+(i-t.y)*(t.next.x-t.x)/(t.next.y-t.y);if(u<=n&&u>r&&(r=u,a=t.x<t.next.x?t:t.next,u===n))return a}t=t.next}while(t!==e);if(!a)return null;let o=a,c=a.x,l=a.y,h=1/0;t=a;do{if(n>=t.x&&t.x>=c&&n!==t.x&&np(i<l?n:r,i,c,l,i<l?r:n,i,t.x,t.y)){let u=Math.abs(i-t.y)/(n-t.x);Ca(t,s)&&(u<h||u===h&&(t.x>a.x||t.x===a.x&&Dg(a,t)))&&(a=t,h=u)}t=t.next}while(t!==o);return a}function Dg(s,e){return Gt(s.prev,s,e.prev)<0&&Gt(e.next,s,s.next)<0}function Ug(s,e,t,n){let i=s;do i.z===0&&(i.z=Rh(i.x,i.y,e,t,n)),i.prevZ=i.prev,i.nextZ=i.next,i=i.next;while(i!==s);i.prevZ.nextZ=null,i.prevZ=null,Fg(i)}function Fg(s){let e,t=1;do{let n=s,i;s=null;let r=null;for(e=0;n;){e++;let a=n,o=0;for(let l=0;l<t&&(o++,a=a.nextZ,!!a);l++);let c=t;for(;o>0||c>0&&a;)o!==0&&(c===0||!a||n.z<=a.z)?(i=n,n=n.nextZ,o--):(i=a,a=a.nextZ,c--),r?r.nextZ=i:s=i,i.prevZ=r,r=i;n=a}r.nextZ=null,t*=2}while(e>1);return s}function Rh(s,e,t,n,i){return s=(s-t)*i|0,e=(e-n)*i|0,s=(s|s<<8)&16711935,s=(s|s<<4)&252645135,s=(s|s<<2)&858993459,s=(s|s<<1)&1431655765,e=(e|e<<8)&16711935,e=(e|e<<4)&252645135,e=(e|e<<2)&858993459,e=(e|e<<1)&1431655765,s|e<<1}function Og(s){let e=s,t=s;do(e.x<t.x||e.x===t.x&&e.y<t.y)&&(t=e),e=e.next;while(e!==s);return t}function np(s,e,t,n,i,r,a,o){return(i-a)*(e-o)>=(s-a)*(r-o)&&(s-a)*(n-o)>=(t-a)*(e-o)&&(t-a)*(r-o)>=(i-a)*(n-o)}function na(s,e,t,n,i,r,a,o){return!(s===a&&e===o)&&np(s,e,t,n,i,r,a,o)}function Bg(s,e){return s.next.i!==e.i&&s.prev.i!==e.i&&!kg(s,e)&&(Ca(s,e)&&Ca(e,s)&&zg(s,e)&&(Gt(s.prev,s,e.prev)||Gt(s,e.prev,e))||wr(s,e)&&Gt(s.prev,s,s.next)>0&&Gt(e.prev,e,e.next)>0)}function Gt(s,e,t){return(e.y-s.y)*(t.x-e.x)-(e.x-s.x)*(t.y-e.y)}function wr(s,e){return s.x===e.x&&s.y===e.y}function ip(s,e,t,n){let i=Go(Gt(s,e,t)),r=Go(Gt(s,e,n)),a=Go(Gt(t,n,s)),o=Go(Gt(t,n,e));return!!(i!==r&&a!==o||i===0&&zo(s,t,e)||r===0&&zo(s,n,e)||a===0&&zo(t,s,n)||o===0&&zo(t,e,n))}function zo(s,e,t){return e.x<=Math.max(s.x,t.x)&&e.x>=Math.min(s.x,t.x)&&e.y<=Math.max(s.y,t.y)&&e.y>=Math.min(s.y,t.y)}function Go(s){return s>0?1:s<0?-1:0}function kg(s,e){let t=s;do{if(t.i!==s.i&&t.next.i!==s.i&&t.i!==e.i&&t.next.i!==e.i&&ip(t,t.next,s,e))return!0;t=t.next}while(t!==s);return!1}function Ca(s,e){return Gt(s.prev,s,s.next)<0?Gt(s,e,s.next)>=0&&Gt(s,s.prev,e)>=0:Gt(s,e,s.prev)<0||Gt(s,s.next,e)<0}function zg(s,e){let t=s,n=!1,i=(s.x+e.x)/2,r=(s.y+e.y)/2;do t.y>r!=t.next.y>r&&t.next.y!==t.y&&i<(t.next.x-t.x)*(r-t.y)/(t.next.y-t.y)+t.x&&(n=!n),t=t.next;while(t!==s);return n}function sp(s,e){let t=Ih(s.i,s.x,s.y),n=Ih(e.i,e.x,e.y),i=s.next,r=e.prev;return s.next=e,e.prev=s,t.next=i,i.prev=t,n.next=t,t.prev=n,r.next=n,n.prev=r,n}function sf(s,e,t,n){let i=Ih(s,e,t);return n?(i.next=n.next,i.prev=n,n.next.prev=i,n.next=i):(i.prev=i,i.next=i),i}function Ra(s){s.next.prev=s.prev,s.prev.next=s.next,s.prevZ&&(s.prevZ.nextZ=s.nextZ),s.nextZ&&(s.nextZ.prevZ=s.prevZ)}function Ih(s,e,t){return{i:s,x:e,y:t,prev:null,next:null,z:0,prevZ:null,nextZ:null,steiner:!1}}function Gg(s,e,t,n){let i=0;for(let r=e,a=t-n;r<t;r+=n)i+=(s[a]-s[r])*(s[r+1]+s[a+1]),a=r;return i}var Ph=class{static triangulate(e,t,n=2){return wg(e,t,n)}},gi=class s{static area(e){let t=e.length,n=0;for(let i=t-1,r=0;r<t;i=r++)n+=e[i].x*e[r].y-e[r].x*e[i].y;return n*.5}static isClockWise(e){return s.area(e)<0}static triangulateShape(e,t){let n=[],i=[],r=[];rf(e),af(n,e);let a=e.length;t.forEach(rf);for(let c=0;c<t.length;c++)i.push(a),a+=t[c].length,af(n,t[c]);let o=Ph.triangulate(n,i);for(let c=0;c<o.length;c+=3)r.push(o.slice(c,c+3));return r}};function rf(s){let e=s.length;e>2&&s[e-1].equals(s[0])&&s.pop()}function af(s,e){for(let t=0;t<e.length;t++)s.push(e[t].x),s.push(e[t].y)}var Ia=class s extends tt{constructor(e=new Vn([new ne(.5,.5),new ne(-.5,.5),new ne(-.5,-.5),new ne(.5,-.5)]),t={}){super(),this.type="ExtrudeGeometry",this.parameters={shapes:e,options:t},e=Array.isArray(e)?e:[e];let n=this,i=[],r=[];for(let o=0,c=e.length;o<c;o++){let l=e[o];a(l)}this.setAttribute("position",new Oe(i,3)),this.setAttribute("uv",new Oe(r,2)),this.computeVertexNormals();function a(o){let c=[],l=t.curveSegments!==void 0?t.curveSegments:12,h=t.steps!==void 0?t.steps:1,u=t.depth!==void 0?t.depth:1,d=t.bevelEnabled!==void 0?t.bevelEnabled:!0,p=t.bevelThickness!==void 0?t.bevelThickness:.2,g=t.bevelSize!==void 0?t.bevelSize:p-.1,v=t.bevelOffset!==void 0?t.bevelOffset:0,f=t.bevelSegments!==void 0?t.bevelSegments:3,m=t.extrudePath,_=t.UVGenerator!==void 0?t.UVGenerator:Vg,b,x=!1,T,S,A,y;if(m){b=m.getSpacedPoints(h),x=!0,d=!1;let ee=m.isCatmullRomCurve3?m.closed:!1;T=m.computeFrenetFrames(h,ee),S=new R,A=new R,y=new R}d||(f=0,p=0,g=0,v=0);let E=o.extractPoints(l),I=E.shape,L=E.holes;if(!gi.isClockWise(I)){I=I.reverse();for(let ee=0,ae=L.length;ee<ae;ee++){let oe=L[ee];gi.isClockWise(oe)&&(L[ee]=oe.reverse())}}function V(ee){let oe=10000000000000001e-36,le=ee[0];for(let ue=1;ue<=ee.length;ue++){let ze=ue%ee.length,Be=ee[ze],qe=Be.x-le.x,$e=Be.y-le.y,P=qe*qe+$e*$e,Mt=Math.max(Math.abs(Be.x),Math.abs(Be.y),Math.abs(le.x),Math.abs(le.y)),ht=oe*Mt*Mt;if(P<=ht){ee.splice(ze,1),ue--;continue}le=Be}}V(I),L.forEach(V);let D=L.length,B=I;for(let ee=0;ee<D;ee++){let ae=L[ee];I=I.concat(ae)}function X(ee,ae,oe){return ae||He("ExtrudeGeometry: vec does not exist"),ee.clone().addScaledVector(ae,oe)}let W=I.length;function re(ee,ae,oe){let le,ue,ze,Be=ee.x-ae.x,qe=ee.y-ae.y,$e=oe.x-ee.x,P=oe.y-ee.y,Mt=Be*Be+qe*qe,ht=Be*P-qe*$e;if(Math.abs(ht)>Number.EPSILON){let C=Math.sqrt(Mt),M=Math.sqrt($e*$e+P*P),O=ae.x-qe/C,G=ae.y+Be/C,Y=oe.x-P/M,ce=oe.y+$e/M,he=((Y-O)*P-(ce-G)*$e)/(Be*P-qe*$e);le=O+Be*he-ee.x,ue=G+qe*he-ee.y;let K=le*le+ue*ue;if(K<=2)return new ne(le,ue);ze=Math.sqrt(K/2)}else{let C=!1;Be>Number.EPSILON?$e>Number.EPSILON&&(C=!0):Be<-Number.EPSILON?$e<-Number.EPSILON&&(C=!0):Math.sign(qe)===Math.sign(P)&&(C=!0),C?(le=-qe,ue=Be,ze=Math.sqrt(Mt)):(le=Be,ue=qe,ze=Math.sqrt(Mt/2))}return new ne(le/ze,ue/ze)}let q=[];for(let ee=0,ae=B.length,oe=ae-1,le=ee+1;ee<ae;ee++,oe++,le++)oe===ae&&(oe=0),le===ae&&(le=0),q[ee]=re(B[ee],B[oe],B[le]);let j=[],te,Ne=q.concat();for(let ee=0,ae=D;ee<ae;ee++){let oe=L[ee];te=[];for(let le=0,ue=oe.length,ze=ue-1,Be=le+1;le<ue;le++,ze++,Be++)ze===ue&&(ze=0),Be===ue&&(Be=0),te[le]=re(oe[le],oe[ze],oe[Be]);j.push(te),Ne=Ne.concat(te)}let Ae;if(f===0)Ae=gi.triangulateShape(B,L);else{let ee=[],ae=[];for(let oe=0;oe<f;oe++){let le=oe/f,ue=p*Math.cos(le*Math.PI/2),ze=g*Math.sin(le*Math.PI/2)+v;for(let Be=0,qe=B.length;Be<qe;Be++){let $e=X(B[Be],q[Be],ze);_e($e.x,$e.y,-ue),le===0&&ee.push($e)}for(let Be=0,qe=D;Be<qe;Be++){let $e=L[Be];te=j[Be];let P=[];for(let Mt=0,ht=$e.length;Mt<ht;Mt++){let C=X($e[Mt],te[Mt],ze);_e(C.x,C.y,-ue),le===0&&P.push(C)}le===0&&ae.push(P)}}Ae=gi.triangulateShape(ee,ae)}let vt=Ae.length,ct=g+v;for(let ee=0;ee<W;ee++){let ae=d?X(I[ee],Ne[ee],ct):I[ee];x?(A.copy(T.normals[0]).multiplyScalar(ae.x),S.copy(T.binormals[0]).multiplyScalar(ae.y),y.copy(b[0]).add(A).add(S),_e(y.x,y.y,y.z)):_e(ae.x,ae.y,0)}for(let ee=1;ee<=h;ee++)for(let ae=0;ae<W;ae++){let oe=d?X(I[ae],Ne[ae],ct):I[ae];x?(A.copy(T.normals[ee]).multiplyScalar(oe.x),S.copy(T.binormals[ee]).multiplyScalar(oe.y),y.copy(b[ee]).add(A).add(S),_e(y.x,y.y,y.z)):_e(oe.x,oe.y,u/h*ee)}for(let ee=f-1;ee>=0;ee--){let ae=ee/f,oe=p*Math.cos(ae*Math.PI/2),le=g*Math.sin(ae*Math.PI/2)+v;for(let ue=0,ze=B.length;ue<ze;ue++){let Be=X(B[ue],q[ue],le);_e(Be.x,Be.y,u+oe)}for(let ue=0,ze=L.length;ue<ze;ue++){let Be=L[ue];te=j[ue];for(let qe=0,$e=Be.length;qe<$e;qe++){let P=X(Be[qe],te[qe],le);x?_e(P.x,P.y+b[h-1].y,b[h-1].x+oe):_e(P.x,P.y,u+oe)}}}mt(),Z();function mt(){let ee=i.length/3;if(d){let ae=0,oe=W*ae;for(let le=0;le<vt;le++){let ue=Ae[le];We(ue[2]+oe,ue[1]+oe,ue[0]+oe)}ae=h+f*2,oe=W*ae;for(let le=0;le<vt;le++){let ue=Ae[le];We(ue[0]+oe,ue[1]+oe,ue[2]+oe)}}else{for(let ae=0;ae<vt;ae++){let oe=Ae[ae];We(oe[2],oe[1],oe[0])}for(let ae=0;ae<vt;ae++){let oe=Ae[ae];We(oe[0]+W*h,oe[1]+W*h,oe[2]+W*h)}}n.addGroup(ee,i.length/3-ee,0)}function Z(){let ee=i.length/3,ae=0;Q(B,ae),ae+=B.length;for(let oe=0,le=L.length;oe<le;oe++){let ue=L[oe];Q(ue,ae),ae+=ue.length}n.addGroup(ee,i.length/3-ee,1)}function Q(ee,ae){let oe=ee.length;for(;--oe>=0;){let le=oe,ue=oe-1;ue<0&&(ue=ee.length-1);for(let ze=0,Be=h+f*2;ze<Be;ze++){let qe=W*ze,$e=W*(ze+1),P=ae+le+qe,Mt=ae+ue+qe,ht=ae+ue+$e,C=ae+le+$e;be(P,Mt,ht,C)}}}function _e(ee,ae,oe){c.push(ee),c.push(ae),c.push(oe)}function We(ee,ae,oe){Xe(ee),Xe(ae),Xe(oe);let le=i.length/3,ue=_.generateTopUV(n,i,le-3,le-2,le-1);Tt(ue[0]),Tt(ue[1]),Tt(ue[2])}function be(ee,ae,oe,le){Xe(ee),Xe(ae),Xe(le),Xe(ae),Xe(oe),Xe(le);let ue=i.length/3,ze=_.generateSideWallUV(n,i,ue-6,ue-3,ue-2,ue-1);Tt(ze[0]),Tt(ze[1]),Tt(ze[3]),Tt(ze[1]),Tt(ze[2]),Tt(ze[3])}function Xe(ee){i.push(c[ee*3+0]),i.push(c[ee*3+1]),i.push(c[ee*3+2])}function Tt(ee){r.push(ee.x),r.push(ee.y)}}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}toJSON(){let e=super.toJSON(),t=this.parameters.shapes,n=this.parameters.options;return Hg(t,n,e)}static fromJSON(e,t){let n=[];for(let r=0,a=e.shapes.length;r<a;r++){let o=t[e.shapes[r]];n.push(o)}let i=e.options.extrudePath;return i!==void 0&&(e.options.extrudePath=new cl[i.type]().fromJSON(i)),new s(n,e.options)}},Vg={generateTopUV:function(s,e,t,n,i){let r=e[t*3],a=e[t*3+1],o=e[n*3],c=e[n*3+1],l=e[i*3],h=e[i*3+1];return[new ne(r,a),new ne(o,c),new ne(l,h)]},generateSideWallUV:function(s,e,t,n,i,r){let a=e[t*3],o=e[t*3+1],c=e[t*3+2],l=e[n*3],h=e[n*3+1],u=e[n*3+2],d=e[i*3],p=e[i*3+1],g=e[i*3+2],v=e[r*3],f=e[r*3+1],m=e[r*3+2];return Math.abs(o-h)<Math.abs(a-l)?[new ne(a,1-c),new ne(l,1-u),new ne(d,1-g),new ne(v,1-m)]:[new ne(o,1-c),new ne(h,1-u),new ne(p,1-g),new ne(f,1-m)]}};function Hg(s,e,t){if(t.shapes=[],Array.isArray(s))for(let n=0,i=s.length;n<i;n++){let r=s[n];t.shapes.push(r.uuid)}else t.shapes.push(s.uuid);return t.options=Object.assign({},e),e.extrudePath!==void 0&&(t.options.extrudePath=e.extrudePath.toJSON()),t}var Vt=class s extends ya{constructor(e=1,t=0){let n=(1+Math.sqrt(5))/2,i=[-1,n,0,1,n,0,-1,-n,0,1,-n,0,0,-1,n,0,1,n,0,-1,-n,0,1,-n,n,0,-1,n,0,1,-n,0,-1,-n,0,1],r=[0,11,5,0,5,1,0,1,7,0,7,10,0,10,11,1,5,9,5,11,4,11,10,2,10,7,6,7,1,8,3,9,4,3,4,2,3,2,6,3,6,8,3,8,9,4,9,5,2,4,11,6,2,10,8,6,7,9,8,1];super(i,r,e,t),this.type="IcosahedronGeometry",this.parameters={radius:e,detail:t}}static fromJSON(e){return new s(e.radius,e.detail)}};var Hn=class s extends ya{constructor(e=1,t=0){let n=[1,0,0,-1,0,0,0,1,0,0,-1,0,0,0,1,0,0,-1],i=[0,2,4,0,4,3,0,3,5,0,5,2,1,2,5,1,5,3,1,3,4,1,4,2];super(n,i,e,t),this.type="OctahedronGeometry",this.parameters={radius:e,detail:t}}static fromJSON(e){return new s(e.radius,e.detail)}},Rt=class s extends tt{constructor(e=1,t=1,n=1,i=1){super(),this.type="PlaneGeometry",this.parameters={width:e,height:t,widthSegments:n,heightSegments:i};let r=e/2,a=t/2,o=Math.floor(n),c=Math.floor(i),l=o+1,h=c+1,u=e/o,d=t/c,p=[],g=[],v=[],f=[];for(let m=0;m<h;m++){let _=m*d-a;for(let b=0;b<l;b++){let x=b*u-r;g.push(x,-_,0),v.push(0,0,1),f.push(b/o),f.push(1-m/c)}}for(let m=0;m<c;m++)for(let _=0;_<o;_++){let b=_+l*m,x=_+l*(m+1),T=_+1+l*(m+1),S=_+1+l*m;p.push(b,x,S),p.push(x,T,S)}this.setIndex(p),this.setAttribute("position",new Oe(g,3)),this.setAttribute("normal",new Oe(v,3)),this.setAttribute("uv",new Oe(f,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.width,e.height,e.widthSegments,e.heightSegments)}},ki=class s extends tt{constructor(e=.5,t=1,n=32,i=1,r=0,a=Math.PI*2){super(),this.type="RingGeometry",this.parameters={innerRadius:e,outerRadius:t,thetaSegments:n,phiSegments:i,thetaStart:r,thetaLength:a},n=Math.max(3,n),i=Math.max(1,i);let o=[],c=[],l=[],h=[],u=e,d=(t-e)/i,p=new R,g=new ne;for(let v=0;v<=i;v++){for(let f=0;f<=n;f++){let m=r+f/n*a;p.x=u*Math.cos(m),p.y=u*Math.sin(m),c.push(p.x,p.y,p.z),l.push(0,0,1),g.x=(p.x/t+1)/2,g.y=(p.y/t+1)/2,h.push(g.x,g.y)}u+=d}for(let v=0;v<i;v++){let f=v*(n+1);for(let m=0;m<n;m++){let _=m+f,b=_,x=_+n+1,T=_+n+2,S=_+1;o.push(b,x,S),o.push(x,T,S)}}this.setIndex(o),this.setAttribute("position",new Oe(c,3)),this.setAttribute("normal",new Oe(l,3)),this.setAttribute("uv",new Oe(h,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.innerRadius,e.outerRadius,e.thetaSegments,e.phiSegments,e.thetaStart,e.thetaLength)}},ls=class s extends tt{constructor(e=new Vn([new ne(0,.5),new ne(-.5,-.5),new ne(.5,-.5)]),t=12){super(),this.type="ShapeGeometry",this.parameters={shapes:e,curveSegments:t};let n=[],i=[],r=[],a=[],o=0,c=0;if(Array.isArray(e)===!1)l(e);else for(let h=0;h<e.length;h++)l(e[h]),this.addGroup(o,c,h),o+=c,c=0;this.setIndex(n),this.setAttribute("position",new Oe(i,3)),this.setAttribute("normal",new Oe(r,3)),this.setAttribute("uv",new Oe(a,2));function l(h){let u=i.length/3,d=h.extractPoints(t),p=d.shape,g=d.holes;gi.isClockWise(p)===!1&&(p=p.reverse());for(let f=0,m=g.length;f<m;f++){let _=g[f];gi.isClockWise(_)===!0&&(g[f]=_.reverse())}let v=gi.triangulateShape(p,g);for(let f=0,m=g.length;f<m;f++){let _=g[f];p=p.concat(_)}for(let f=0,m=p.length;f<m;f++){let _=p[f];i.push(_.x,_.y,0),r.push(0,0,1),a.push(_.x,_.y)}for(let f=0,m=v.length;f<m;f++){let _=v[f],b=_[0]+u,x=_[1]+u,T=_[2]+u;n.push(b,x,T),c+=3}}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}toJSON(){let e=super.toJSON(),t=this.parameters.shapes;return Wg(t,e)}static fromJSON(e,t){let n=[];for(let i=0,r=e.shapes.length;i<r;i++){let a=t[e.shapes[i]];n.push(a)}return new s(n,e.curveSegments)}};function Wg(s,e){if(e.shapes=[],Array.isArray(s))for(let t=0,n=s.length;t<n;t++){let i=s[t];e.shapes.push(i.uuid)}else e.shapes.push(s.uuid);return e}var Nt=class s extends tt{constructor(e=1,t=32,n=16,i=0,r=Math.PI*2,a=0,o=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius:e,widthSegments:t,heightSegments:n,phiStart:i,phiLength:r,thetaStart:a,thetaLength:o},t=Math.max(3,Math.floor(t)),n=Math.max(2,Math.floor(n));let c=Math.min(a+o,Math.PI),l=0,h=[],u=new R,d=new R,p=[],g=[],v=[],f=[];for(let m=0;m<=n;m++){let _=[],b=m/n,x=a+b*o,T=e*Math.cos(x),S=Math.sqrt(e*e-T*T),A=0;m===0&&a===0?A=.5/t:m===n&&c===Math.PI&&(A=-.5/t);for(let y=0;y<=t;y++){let E=y/t,I=i+E*r;u.x=-S*Math.cos(I),u.y=T,u.z=S*Math.sin(I),g.push(u.x,u.y,u.z),d.copy(u).normalize(),v.push(d.x,d.y,d.z),f.push(E+A,1-b),_.push(l++)}h.push(_)}for(let m=0;m<n;m++)for(let _=0;_<t;_++){let b=h[m][_+1],x=h[m][_],T=h[m+1][_],S=h[m+1][_+1];(m!==0||a>0)&&p.push(b,x,S),(m!==n-1||c<Math.PI)&&p.push(x,T,S)}this.setIndex(p),this.setAttribute("position",new Oe(g,3)),this.setAttribute("normal",new Oe(v,3)),this.setAttribute("uv",new Oe(f,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.radius,e.widthSegments,e.heightSegments,e.phiStart,e.phiLength,e.thetaStart,e.thetaLength)}};var si=class s extends tt{constructor(e=1,t=.4,n=12,i=48,r=Math.PI*2,a=0,o=Math.PI*2){super(),this.type="TorusGeometry",this.parameters={radius:e,tube:t,radialSegments:n,tubularSegments:i,arc:r,thetaStart:a,thetaLength:o},n=Math.floor(n),i=Math.floor(i);let c=[],l=[],h=[],u=[],d=new R,p=new R,g=new R;for(let v=0;v<=n;v++){let f=a+v/n*o;for(let m=0;m<=i;m++){let _=m/i*r;p.x=(e+t*Math.cos(f))*Math.cos(_),p.y=(e+t*Math.cos(f))*Math.sin(_),p.z=t*Math.sin(f),l.push(p.x,p.y,p.z),d.x=e*Math.cos(_),d.y=e*Math.sin(_),g.subVectors(p,d).normalize(),h.push(g.x,g.y,g.z),u.push(m/i),u.push(v/n)}}for(let v=1;v<=n;v++)for(let f=1;f<=i;f++){let m=(i+1)*v+f-1,_=(i+1)*(v-1)+f-1,b=(i+1)*(v-1)+f,x=(i+1)*v+f;c.push(m,_,x),c.push(_,b,x)}this.setIndex(c),this.setAttribute("position",new Oe(l,3)),this.setAttribute("normal",new Oe(h,3)),this.setAttribute("uv",new Oe(u,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new s(e.radius,e.tube,e.radialSegments,e.tubularSegments,e.arc,e.thetaStart,e.thetaLength)}};var Wn=class s extends tt{constructor(e=new Ta(new R(-1,-1,0),new R(-1,1,0),new R(1,1,0)),t=64,n=1,i=8,r=!1){super(),this.type="TubeGeometry",this.parameters={path:e,tubularSegments:t,radius:n,radialSegments:i,closed:r};let a=e.computeFrenetFrames(t,r);this.tangents=a.tangents,this.normals=a.normals,this.binormals=a.binormals;let o=new R,c=new R,l=new ne,h=new R,u=[],d=[],p=[],g=[];v(),this.setIndex(g),this.setAttribute("position",new Oe(u,3)),this.setAttribute("normal",new Oe(d,3)),this.setAttribute("uv",new Oe(p,2));function v(){for(let b=0;b<t;b++)f(b);f(r===!1?t:0),_(),m()}function f(b){h=e.getPointAt(b/t,h);let x=a.normals[b],T=a.binormals[b];for(let S=0;S<=i;S++){let A=S/i*Math.PI*2,y=Math.sin(A),E=-Math.cos(A);c.x=E*x.x+y*T.x,c.y=E*x.y+y*T.y,c.z=E*x.z+y*T.z,c.normalize(),d.push(c.x,c.y,c.z),o.x=h.x+n*c.x,o.y=h.y+n*c.y,o.z=h.z+n*c.z,u.push(o.x,o.y,o.z)}}function m(){for(let b=1;b<=t;b++)for(let x=1;x<=i;x++){let T=(i+1)*(b-1)+(x-1),S=(i+1)*b+(x-1),A=(i+1)*b+x,y=(i+1)*(b-1)+x;g.push(T,S,y),g.push(S,A,y)}}function _(){for(let b=0;b<=t;b++)for(let x=0;x<=i;x++)l.x=b/t,l.y=x/i,p.push(l.x,l.y)}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}toJSON(){let e=super.toJSON();return e.path=this.parameters.path.toJSON(),e}static fromJSON(e){return new s(new cl[e.path.type]().fromJSON(e.path),e.tubularSegments,e.radius,e.radialSegments,e.closed)}};function ks(s){let e={};for(let t in s){e[t]={};for(let n in s[t]){let i=s[t][n];if(of(i))i.isRenderTargetTexture?(Le("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),e[t][n]=null):e[t][n]=i.clone();else if(Array.isArray(i))if(of(i[0])){let r=[];for(let a=0,o=i.length;a<o;a++)r[a]=i[a].clone();e[t][n]=r}else e[t][n]=i.slice();else e[t][n]=i}}return e}function dn(s){let e={};for(let t=0;t<s.length;t++){let n=ks(s[t]);for(let i in n)e[i]=n[i]}return e}function of(s){return s&&(s.isColor||s.isMatrix3||s.isMatrix4||s.isVector2||s.isVector3||s.isVector4||s.isTexture||s.isQuaternion)}function Xg(s){let e=[];for(let t=0;t<s.length;t++)e.push(s[t].clone());return e}function iu(s){let e=s.getRenderTarget();return e===null?s.outputColorSpace:e.isXRRenderTarget===!0?e.texture.colorSpace:it.workingColorSpace}var qi={clone:ks,merge:dn},qg=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,Yg=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`,Bt=class extends xn{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=qg,this.fragmentShader=Yg,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=ks(e.uniforms),this.uniformsGroups=Xg(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this.defaultAttributeValues=Object.assign({},e.defaultAttributeValues),this.index0AttributeName=e.index0AttributeName,this.uniformsNeedUpdate=e.uniformsNeedUpdate,this}toJSON(e){let t=super.toJSON(e);t.glslVersion=this.glslVersion,t.uniforms={};for(let i in this.uniforms){let a=this.uniforms[i].value;a&&a.isTexture?t.uniforms[i]={type:"t",value:a.toJSON(e).uuid}:a&&a.isColor?t.uniforms[i]={type:"c",value:a.getHex()}:a&&a.isVector2?t.uniforms[i]={type:"v2",value:a.toArray()}:a&&a.isVector3?t.uniforms[i]={type:"v3",value:a.toArray()}:a&&a.isVector4?t.uniforms[i]={type:"v4",value:a.toArray()}:a&&a.isMatrix3?t.uniforms[i]={type:"m3",value:a.toArray()}:a&&a.isMatrix4?t.uniforms[i]={type:"m4",value:a.toArray()}:t.uniforms[i]={value:a}}Object.keys(this.defines).length>0&&(t.defines=this.defines),t.vertexShader=this.vertexShader,t.fragmentShader=this.fragmentShader,t.lights=this.lights,t.clipping=this.clipping;let n={};for(let i in this.extensions)this.extensions[i]===!0&&(n[i]=!0);return Object.keys(n).length>0&&(t.extensions=n),t}fromJSON(e,t){if(super.fromJSON(e,t),e.uniforms!==void 0)for(let n in e.uniforms){let i=e.uniforms[n];switch(this.uniforms[n]={},i.type){case"t":this.uniforms[n].value=t[i.value]||null;break;case"c":this.uniforms[n].value=new Me().setHex(i.value);break;case"v2":this.uniforms[n].value=new ne().fromArray(i.value);break;case"v3":this.uniforms[n].value=new R().fromArray(i.value);break;case"v4":this.uniforms[n].value=new At().fromArray(i.value);break;case"m3":this.uniforms[n].value=new Ze().fromArray(i.value);break;case"m4":this.uniforms[n].value=new je().fromArray(i.value);break;default:this.uniforms[n].value=i.value}}if(e.defines!==void 0&&(this.defines=e.defines),e.vertexShader!==void 0&&(this.vertexShader=e.vertexShader),e.fragmentShader!==void 0&&(this.fragmentShader=e.fragmentShader),e.glslVersion!==void 0&&(this.glslVersion=e.glslVersion),e.extensions!==void 0)for(let n in e.extensions)this.extensions[n]=e.extensions[n];return e.lights!==void 0&&(this.lights=e.lights),e.clipping!==void 0&&(this.clipping=e.clipping),this}},Ar=class extends Bt{constructor(e){super(e),this.isRawShaderMaterial=!0,this.type="RawShaderMaterial"}},nt=class extends xn{constructor(e){super(),this.isMeshStandardMaterial=!0,this.type="MeshStandardMaterial",this.defines={STANDARD:""},this.color=new Me(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Me(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=oc,this.normalScale=new ne(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Oi,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.defines={STANDARD:""},this.color.copy(e.color),this.roughness=e.roughness,this.metalness=e.metalness,this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.emissive.copy(e.emissive),this.emissiveMap=e.emissiveMap,this.emissiveIntensity=e.emissiveIntensity,this.bumpMap=e.bumpMap,this.bumpScale=e.bumpScale,this.normalMap=e.normalMap,this.normalMapType=e.normalMapType,this.normalScale.copy(e.normalScale),this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.roughnessMap=e.roughnessMap,this.metalnessMap=e.metalnessMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.envMapIntensity=e.envMapIntensity,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.flatShading=e.flatShading,this.fog=e.fog,this}},It=class extends nt{constructor(e){super(),this.isMeshPhysicalMaterial=!0,this.defines={STANDARD:"",PHYSICAL:""},this.type="MeshPhysicalMaterial",this.anisotropyRotation=0,this.anisotropyMap=null,this.clearcoatMap=null,this.clearcoatRoughness=0,this.clearcoatRoughnessMap=null,this.clearcoatNormalScale=new ne(1,1),this.clearcoatNormalMap=null,this.ior=1.5,Object.defineProperty(this,"reflectivity",{get:function(){return ot(2.5*(this.ior-1)/(this.ior+1),0,1)},set:function(t){this.ior=(1+.4*t)/(1-.4*t)}}),this.iridescenceMap=null,this.iridescenceIOR=1.3,this.iridescenceThicknessRange=[100,400],this.iridescenceThicknessMap=null,this.sheenColor=new Me(0),this.sheenColorMap=null,this.sheenRoughness=1,this.sheenRoughnessMap=null,this.transmissionMap=null,this.thickness=0,this.thicknessMap=null,this.attenuationDistance=1/0,this.attenuationColor=new Me(1,1,1),this.specularIntensity=1,this.specularIntensityMap=null,this.specularColor=new Me(1,1,1),this.specularColorMap=null,this._anisotropy=0,this._clearcoat=0,this._dispersion=0,this._iridescence=0,this._retroreflectivity=0,this._sheen=0,this._transmission=0,this.setValues(e)}get anisotropy(){return this._anisotropy}set anisotropy(e){this._anisotropy>0!=e>0&&this.version++,this._anisotropy=e}get clearcoat(){return this._clearcoat}set clearcoat(e){this._clearcoat>0!=e>0&&this.version++,this._clearcoat=e}get iridescence(){return this._iridescence}set iridescence(e){this._iridescence>0!=e>0&&this.version++,this._iridescence=e}get dispersion(){return this._dispersion}set dispersion(e){this._dispersion>0!=e>0&&this.version++,this._dispersion=e}get retroreflectivity(){return this._retroreflectivity}set retroreflectivity(e){this._retroreflectivity>0!=e>0&&this.version++,this._retroreflectivity=e}get sheen(){return this._sheen}set sheen(e){this._sheen>0!=e>0&&this.version++,this._sheen=e}get transmission(){return this._transmission}set transmission(e){this._transmission>0!=e>0&&this.version++,this._transmission=e}copy(e){return super.copy(e),this.defines={STANDARD:"",PHYSICAL:""},this.anisotropy=e.anisotropy,this.anisotropyRotation=e.anisotropyRotation,this.anisotropyMap=e.anisotropyMap,this.clearcoat=e.clearcoat,this.clearcoatMap=e.clearcoatMap,this.clearcoatRoughness=e.clearcoatRoughness,this.clearcoatRoughnessMap=e.clearcoatRoughnessMap,this.clearcoatNormalMap=e.clearcoatNormalMap,this.clearcoatNormalScale.copy(e.clearcoatNormalScale),this.dispersion=e.dispersion,this.ior=e.ior,this.iridescence=e.iridescence,this.iridescenceMap=e.iridescenceMap,this.iridescenceIOR=e.iridescenceIOR,this.iridescenceThicknessRange=[...e.iridescenceThicknessRange],this.iridescenceThicknessMap=e.iridescenceThicknessMap,this.retroreflectivity=e.retroreflectivity,this.sheen=e.sheen,this.sheenColor.copy(e.sheenColor),this.sheenColorMap=e.sheenColorMap,this.sheenRoughness=e.sheenRoughness,this.sheenRoughnessMap=e.sheenRoughnessMap,this.transmission=e.transmission,this.transmissionMap=e.transmissionMap,this.thickness=e.thickness,this.thicknessMap=e.thicknessMap,this.attenuationDistance=e.attenuationDistance,this.attenuationColor.copy(e.attenuationColor),this.specularIntensity=e.specularIntensity,this.specularIntensityMap=e.specularIntensityMap,this.specularColor.copy(e.specularColor),this.specularColorMap=e.specularColorMap,this}};var ul=class extends xn{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=zf,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}},dl=class extends xn{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}};function is(s,e){return!s||s.constructor===e?s:typeof e.BYTES_PER_ELEMENT=="number"?new e(s):Array.prototype.slice.call(s)}function qo(s){return s!==void 0&&s.inTangents!==void 0&&s.outTangents!==void 0}function Kg(s){function e(i,r){return s[i]-s[r]}let t=s.length,n=new Array(t);for(let i=0;i!==t;++i)n[i]=i;return n.sort(e),n}function lf(s,e,t){let n=s.length,i=new s.constructor(n);for(let r=0,a=0;a!==n;++r){let o=t[r]*e;for(let c=0;c!==e;++c)i[a++]=s[o+c]}return i}function Zg(s,e,t,n){let i=1,r=s[0];for(;r!==void 0&&r[n]===void 0;)r=s[i++];if(r===void 0)return;let a=r[n];if(a!==void 0)if(Array.isArray(a))do a=r[n],a!==void 0&&(e.push(r.time),t.push(...a)),r=s[i++];while(r!==void 0);else if(a.toArray!==void 0)do a=r[n],a!==void 0&&(e.push(r.time),a.toArray(t,t.length)),r=s[i++];while(r!==void 0);else do a=r[n],a!==void 0&&(e.push(r.time),t.push(a)),r=s[i++];while(r!==void 0)}var Si=class{constructor(e,t,n,i){this.parameterPositions=e,this._cachedIndex=0,this.resultBuffer=i!==void 0?i:new t.constructor(n),this.sampleValues=t,this.valueSize=n,this.settings=null,this.DefaultSettings_={}}evaluate(e){let t=this.parameterPositions,n=this._cachedIndex,i=t[n],r=t[n-1];n:{e:{let a;t:{i:if(!(e<i)){for(let o=n+2;;){if(i===void 0){if(e<r)break i;return n=t.length,this._cachedIndex=n,this.copySampleValue_(n-1)}if(n===o)break;if(r=i,i=t[++n],e<i)break e}a=t.length;break t}if(!(e>=r)){let o=t[1];e<o&&(n=2,r=o);for(let c=n-2;;){if(r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(n===c)break;if(i=r,r=t[--n-1],e>=r)break e}a=n,n=0;break t}break n}for(;n<a;){let o=n+a>>>1;e<t[o]?a=o:n=o+1}if(i=t[n],r=t[n-1],r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(i===void 0)return n=t.length,this._cachedIndex=n,this.copySampleValue_(n-1)}this._cachedIndex=n,this.intervalChanged_(n,r,i)}return this.interpolate_(n,r,e,i)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(e){let t=this.resultBuffer,n=this.sampleValues,i=this.valueSize,r=e*i;for(let a=0;a!==i;++a)t[a]=n[r+a];return t}interpolate_(){throw new Error("THREE.Interpolant: Call to abstract method.")}intervalChanged_(){}},fl=class extends Si{constructor(e,t,n,i){super(e,t,n,i),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:wh,endingEnd:wh}}intervalChanged_(e,t,n){let i=this.parameterPositions,r=e-2,a=e+1,o=i[r],c=i[a];if(o===void 0)switch(this.getSettings_().endingStart){case Ah:r=e,o=2*t-n;break;case Eh:r=i.length-2,o=t+i[r]-i[r+1];break;default:r=e,o=n}if(c===void 0)switch(this.getSettings_().endingEnd){case Ah:a=e,c=2*n-t;break;case Eh:a=1,c=n+i[1]-i[0];break;default:a=e-1,c=t}let l=(n-t)*.5,h=this.valueSize;this._weightPrev=l/(t-o),this._weightNext=l/(c-n),this._offsetPrev=r*h,this._offsetNext=a*h}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,h=this._offsetPrev,u=this._offsetNext,d=this._weightPrev,p=this._weightNext,g=(n-t)/(i-t),v=g*g,f=v*g,m=-d*f+2*d*v-d*g,_=(1+d)*f+(-1.5-2*d)*v+(-.5+d)*g+1,b=(-1-p)*f+(1.5+p)*v+.5*g,x=p*f-p*v;for(let T=0;T!==o;++T)r[T]=m*a[h+T]+_*a[l+T]+b*a[c+T]+x*a[u+T];return r}},pl=class extends Si{constructor(e,t,n,i){super(e,t,n,i)}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,h=(n-t)/(i-t),u=1-h;for(let d=0;d!==o;++d)r[d]=a[l+d]*u+a[c+d]*h;return r}},ml=class extends Si{constructor(e,t,n,i){super(e,t,n,i)}interpolate_(e){return this.copySampleValue_(e-1)}},gl=class extends Si{interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,h=this.inTangents,u=this.outTangents;if(!h||!u){let g=(n-t)/(i-t),v=1-g;for(let f=0;f!==o;++f)r[f]=a[l+f]*v+a[c+f]*g;return r}let d=o*2,p=e-1;for(let g=0;g!==o;++g){let v=a[l+g],f=a[c+g],m=p*d+g*2,_=u[m],b=u[m+1],x=e*d+g*2,T=h[x],S=h[x+1],A=$g(n,t,_,T,i);r[g]=rp(A,v,b,S,f)}return r}};function rp(s,e,t,n,i){let r=1-s;return r*r*r*e+3*r*r*s*t+3*r*s*s*n+s*s*s*i}function Jg(s,e,t,n,i){let r=1-s;return 3*r*r*(t-e)+6*r*s*(n-t)+3*s*s*(i-n)}function $g(s,e,t,n,i){let r=(s-e)/(i-e);for(let a=0;a<8;a++){let o=rp(r,e,t,n,i)-s;if(Math.abs(o)<1e-10)break;let c=Jg(r,e,t,n,i);if(Math.abs(c)<1e-10)break;r=Math.max(0,Math.min(1,r-o/c))}return r}var Sn=class{constructor(e,t,n,i){if(e===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(t===void 0||t.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+e);this.name=e,this.times=is(t,this.TimeBufferType),this.values=is(n,this.ValueBufferType),this.setInterpolation(i||this.DefaultInterpolation)}static toJSON(e){let t=e.constructor,n;if(t.toJSON!==this.toJSON)n=t.toJSON(e);else{n={name:e.name,times:is(e.times,Array),values:is(e.values,Array)};let i=e.getInterpolation();i!==e.DefaultInterpolation&&(n.interpolation=i),qo(e.settings)&&(n.settings={inTangents:is(e.settings.inTangents,Array),outTangents:is(e.settings.outTangents,Array)})}return n.type=e.ValueTypeName,n}InterpolantFactoryMethodDiscrete(e){return new ml(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodLinear(e){return new pl(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodSmooth(e){return new fl(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodBezier(e){let t=new gl(this.times,this.values,this.getValueSize(),e);return this.settings&&(t.inTangents=this.settings.inTangents,t.outTangents=this.settings.outTangents),t}setInterpolation(e){let t;switch(e){case Ts:t=this.InterpolantFactoryMethodDiscrete;break;case ws:t=this.InterpolantFactoryMethodLinear;break;case Wo:t=this.InterpolantFactoryMethodSmooth;break;case Th:t=this.InterpolantFactoryMethodBezier;break}if(t===void 0){let n="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(e!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(n);return Le("KeyframeTrack:",n),this}return this.createInterpolant=t,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return Ts;case this.InterpolantFactoryMethodLinear:return ws;case this.InterpolantFactoryMethodSmooth:return Wo;case this.InterpolantFactoryMethodBezier:return Th}}getValueSize(){return this.values.length/this.times.length}shift(e){if(e!==0){let t=this.times;for(let n=0,i=t.length;n!==i;++n)t[n]+=e}return this}scale(e){if(e!==1){let t=this.times;for(let n=0,i=t.length;n!==i;++n)t[n]*=e;qo(this.settings)&&(cf(this.settings.inTangents,e),cf(this.settings.outTangents,e))}return this}trim(e,t){let n=this.times,i=n.length,r=0,a=i-1;for(;r!==i&&n[r]<e;)++r;for(;a!==-1&&n[a]>t;)--a;if(++a,r!==0||a!==i){r>=a&&(a=Math.max(a,1),r=a-1);let o=this.getValueSize();this.times=n.slice(r,a),this.values=this.values.slice(r*o,a*o)}return this}validate(){let e=!0,t=this.getValueSize();t-Math.floor(t)!==0&&(He("KeyframeTrack: Invalid value size in track.",this),e=!1);let n=this.times,i=this.values,r=n.length;r===0&&(He("KeyframeTrack: Track is empty.",this),e=!1);let a=null;for(let o=0;o!==r;o++){let c=n[o];if(typeof c=="number"&&isNaN(c)){He("KeyframeTrack: Time is not a valid number.",this,o,c),e=!1;break}if(a!==null&&a>c){He("KeyframeTrack: Out of order keys.",this,o,c,a),e=!1;break}a=c}if(i!==void 0&&Dm(i))for(let o=0,c=i.length;o!==c;++o){let l=i[o];if(isNaN(l)){He("KeyframeTrack: Value is not a valid number.",this,o,l),e=!1;break}}return e}optimize(){let e=this.times.slice(),t=this.values.slice(),n=this.getValueSize(),i=this.getInterpolation()===Wo,r=e.length-1,a=1;for(let o=1;o<r;++o){let c=!1,l=e[o],h=e[o+1];if(l!==h&&(o!==1||l!==e[0]))if(i)c=!0;else{let u=o*n,d=u-n,p=u+n;for(let g=0;g!==n;++g){let v=t[u+g];if(v!==t[d+g]||v!==t[p+g]){c=!0;break}}}if(c){if(o!==a){e[a]=e[o];let u=o*n,d=a*n;for(let p=0;p!==n;++p)t[d+p]=t[u+p]}++a}}if(r>0){e[a]=e[r];for(let o=r*n,c=a*n,l=0;l!==n;++l)t[c+l]=t[o+l];++a}return a!==e.length?(this.times=e.slice(0,a),this.values=t.slice(0,a*n)):(this.times=e,this.values=t),this}clone(){let e=this.times.slice(),t=this.values.slice(),n=this.constructor,i=new n(this.name,e,t);return i.createInterpolant=this.createInterpolant,qo(this.settings)&&(i.settings={inTangents:this.settings.inTangents.slice(),outTangents:this.settings.outTangents.slice()}),i}};function cf(s,e){for(let t=0,n=s.length;t!==n;t+=2)s[t]*=e}Sn.prototype.ValueTypeName="";Sn.prototype.TimeBufferType=Float32Array;Sn.prototype.ValueBufferType=Float32Array;Sn.prototype.DefaultInterpolation=ws;var zi=class extends Sn{constructor(e,t,n){super(e,t,n)}};zi.prototype.ValueTypeName="bool";zi.prototype.ValueBufferType=Array;zi.prototype.DefaultInterpolation=Ts;zi.prototype.InterpolantFactoryMethodLinear=void 0;zi.prototype.InterpolantFactoryMethodSmooth=void 0;var Pa=class extends Sn{constructor(e,t,n,i){super(e,t,n,i)}};Pa.prototype.ValueTypeName="color";var Gi=class extends Sn{constructor(e,t,n,i){super(e,t,n,i)}};Gi.prototype.ValueTypeName="number";var xl=class extends Si{constructor(e,t,n,i){super(e,t,n,i)}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=(n-t)/(i-t),l=e*o;for(let h=l+o;l!==h;l+=4)nn.slerpFlat(r,0,a,l-o,a,l,c);return r}},Vi=class extends Sn{constructor(e,t,n,i){super(e,t,n,i)}InterpolantFactoryMethodLinear(e){return new xl(this.times,this.values,this.getValueSize(),e)}};Vi.prototype.ValueTypeName="quaternion";Vi.prototype.InterpolantFactoryMethodSmooth=void 0;var Hi=class extends Sn{constructor(e,t,n){super(e,t,n)}};Hi.prototype.ValueTypeName="string";Hi.prototype.ValueBufferType=Array;Hi.prototype.DefaultInterpolation=Ts;Hi.prototype.InterpolantFactoryMethodLinear=void 0;Hi.prototype.InterpolantFactoryMethodSmooth=void 0;var cs=class extends Sn{constructor(e,t,n,i){super(e,t,n,i)}};cs.prototype.ValueTypeName="vector";var La=class{constructor(e="",t=-1,n=[],i=kf){this.name=e,this.tracks=n,this.duration=t,this.blendMode=i,this.uuid=kn(),this.userData={},this.duration<0&&this.resetDuration()}static parse(e){let t=[],n=e.tracks,i=1/(e.fps||1);for(let a=0,o=n.length;a!==o;++a)t.push(Qg(n[a]).scale(i));let r=new this(e.name,e.duration,t,e.blendMode);return r.uuid=e.uuid,r.userData=JSON.parse(e.userData||"{}"),r}static toJSON(e){let t=[],n=e.tracks,i={name:e.name,duration:e.duration,tracks:t,uuid:e.uuid,blendMode:e.blendMode,userData:JSON.stringify(e.userData)};for(let r=0,a=n.length;r!==a;++r)t.push(Sn.toJSON(n[r]));return i}static CreateFromMorphTargetSequence(e,t,n,i){let r=t.length,a=[];for(let o=0;o<r;o++){let c=[],l=[];c.push((o+r-1)%r,o,(o+1)%r),l.push(0,1,0);let h=Kg(c);c=lf(c,1,h),l=lf(l,1,h),!i&&c[0]===0&&(c.push(r),l.push(l[0])),a.push(new Gi(".morphTargetInfluences["+t[o].name+"]",c,l).scale(1/n))}return new this(e,-1,a)}static findByName(e,t){let n=e;if(!Array.isArray(e)){let i=e;n=i.geometry&&i.geometry.animations||i.animations}for(let i=0;i<n.length;i++)if(n[i].name===t)return n[i];return null}static CreateClipsFromMorphTargetSequences(e,t,n){let i={},r=/^([\w-]*?)([\d]+)$/;for(let o=0,c=e.length;o<c;o++){let l=e[o],h=l.name.match(r);if(h&&h.length>1){let u=h[1],d=i[u];d||(i[u]=d=[]),d.push(l)}}let a=[];for(let o in i)a.push(this.CreateFromMorphTargetSequence(o,i[o],t,n));return a}resetDuration(){let e=this.tracks,t=0;for(let n=0,i=e.length;n!==i;++n){let r=this.tracks[n];t=Math.max(t,r.times[r.times.length-1])}return this.duration=t,this}trim(){for(let e=0;e<this.tracks.length;e++)this.tracks[e].trim(0,this.duration);return this}validate(){let e=!0;for(let t=0;t<this.tracks.length;t++)e=e&&this.tracks[t].validate();return e}optimize(){for(let e=0;e<this.tracks.length;e++)this.tracks[e].optimize();return this}clone(){let e=[];for(let n=0;n<this.tracks.length;n++)e.push(this.tracks[n].clone());let t=new this.constructor(this.name,this.duration,e,this.blendMode);return t.userData=JSON.parse(JSON.stringify(this.userData)),t}toJSON(){return this.constructor.toJSON(this)}};function jg(s){switch(s.toLowerCase()){case"scalar":case"double":case"float":case"number":case"integer":return Gi;case"vector":case"vector2":case"vector3":case"vector4":return cs;case"color":return Pa;case"quaternion":return Vi;case"bool":case"boolean":return zi;case"string":return Hi}throw new Error("THREE.KeyframeTrack: Unsupported typeName: "+s)}function Qg(s){if(s.type===void 0)throw new Error("THREE.KeyframeTrack: track type undefined, can not parse");let e=jg(s.type);if(s.times===void 0){let n=[],i=[];Zg(s.keys,n,i,"value"),s.times=n,s.values=i}let t;return e.parse!==void 0?t=e.parse(s):t=new e(s.name,s.times,s.values,s.interpolation),qo(s.settings)&&(t.settings={inTangents:is(s.settings.inTangents,Float32Array),outTangents:is(s.settings.outTangents,Float32Array)}),t}var xi={enabled:!1,files:{},add:function(s,e){this.enabled!==!1&&(hf(s)||(this.files[s]=e))},get:function(s){if(this.enabled!==!1&&!hf(s))return this.files[s]},remove:function(s){delete this.files[s]},clear:function(){this.files={}}};function hf(s){try{let e=s.slice(s.indexOf(":")+1);return new URL(e).protocol==="blob:"}catch{return!1}}var _l=class{constructor(e,t,n){let i=this,r=!1,a=0,o=0,c,l=[];this.onStart=void 0,this.onLoad=e,this.onProgress=t,this.onError=n,this._abortController=null,this.itemStart=function(h){o++,r===!1&&i.onStart!==void 0&&i.onStart(h,a,o),r=!0},this.itemEnd=function(h){a++,i.onProgress!==void 0&&i.onProgress(h,a,o),a===o&&(r=!1,i.onLoad!==void 0&&i.onLoad())},this.itemError=function(h){i.onError!==void 0&&i.onError(h)},this.resolveURL=function(h){return h=h.normalize("NFC"),c?c(h):h},this.setURLModifier=function(h){return c=h,this},this.addHandler=function(h,u){return l.push(h,u),this},this.removeHandler=function(h){let u=l.indexOf(h);return u!==-1&&l.splice(u,2),this},this.getHandler=function(h){for(let u=0,d=l.length;u<d;u+=2){let p=l[u],g=l[u+1];if(p.global&&(p.lastIndex=0),p.test(h))return g}return null},this.abort=function(){return this.abortController.abort(),this._abortController=null,this}}get abortController(){return this._abortController||(this._abortController=new AbortController),this._abortController}},ap=new _l,bi=class{constructor(e){this.manager=e!==void 0?e:ap,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}load(){}loadAsync(e,t){let n=this;return new Promise(function(i,r){n.load(e,i,t,r)})}parse(){}setCrossOrigin(e){return this.crossOrigin=e,this}setWithCredentials(e){return this.withCredentials=e,this}setPath(e){return this.path=e,this}setResourcePath(e){return this.resourcePath=e,this}setRequestHeader(e){return this.requestHeader=e,this}abort(){return this}};bi.DEFAULT_MATERIAL_NAME="__DEFAULT";var Ui={},Lh=class extends Error{constructor(e,t){super(e),this.response=t}},Er=class extends bi{constructor(e){super(e),this.mimeType="",this.responseType="",this._abortController=new AbortController}load(e,t,n,i){e===void 0&&(e=""),this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=xi.get(`file:${e}`);if(r!==void 0){this.manager.itemStart(e),setTimeout(()=>{t&&t(r),this.manager.itemEnd(e)},0);return}if(Ui[e]!==void 0){Ui[e].push({onLoad:t,onProgress:n,onError:i});return}Ui[e]=[],Ui[e].push({onLoad:t,onProgress:n,onError:i});let a=new Request(e,{headers:new Headers(this.requestHeader),credentials:this.withCredentials?"include":"same-origin",signal:typeof AbortSignal.any=="function"?AbortSignal.any([this._abortController.signal,this.manager.abortController.signal]):this._abortController.signal}),o=this.mimeType,c=this.responseType;fetch(a).then(l=>{if(l.status===200||l.status===0){if(l.status===0&&Le("FileLoader: HTTP Status 0 received."),typeof ReadableStream>"u"||l.body===void 0||l.body.getReader===void 0)return l;let h=Ui[e],u=l.body.getReader(),d=l.headers.get("X-File-Size")||l.headers.get("Content-Length"),p=d?parseInt(d):0,g=p!==0,v=0,f=new ReadableStream({start(m){_();function _(){u.read().then(({done:b,value:x})=>{if(b)m.close();else{v+=x.byteLength;let T=new ProgressEvent("progress",{lengthComputable:g,loaded:v,total:p});for(let S=0,A=h.length;S<A;S++){let y=h[S];y.onProgress&&y.onProgress(T)}m.enqueue(x),_()}},b=>{m.error(b)})}}});return new Response(f)}else throw new Lh(`fetch for "${l.url}" responded with ${l.status}: ${l.statusText}`,l)}).then(l=>{switch(c){case"arraybuffer":return l.arrayBuffer();case"blob":return l.blob();case"document":return l.text().then(h=>new DOMParser().parseFromString(h,o));case"json":return l.json();default:if(o==="")return l.text();{let u=/charset="?([^;"\s]*)"?/i.exec(o),d=u&&u[1]?u[1].toLowerCase():void 0,p=new TextDecoder(d);return l.arrayBuffer().then(g=>p.decode(g))}}}).then(l=>{xi.add(`file:${e}`,l);let h=Ui[e];delete Ui[e];for(let u=0,d=h.length;u<d;u++){let p=h[u];p.onLoad&&p.onLoad(l)}}).catch(l=>{let h=Ui[e];if(h===void 0)throw this.manager.itemError(e),l;delete Ui[e];for(let u=0,d=h.length;u<d;u++){let p=h[u];p.onError&&p.onError(l)}this.manager.itemError(e)}).finally(()=>{this.manager.itemEnd(e)}),this.manager.itemStart(e)}setResponseType(e){return this.responseType=e,this}setMimeType(e){return this.mimeType=e,this}abort(){return this._abortController.abort(),this._abortController=new AbortController,this}};var cr=new WeakMap,yl=class extends bi{constructor(e){super(e)}load(e,t,n,i){this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=this,a=xi.get(`image:${e}`);if(a!==void 0){if(a.complete===!0)r.manager.itemStart(e),setTimeout(function(){t&&t(a),r.manager.itemEnd(e)},0);else{let u=cr.get(a);u===void 0&&(u=[],cr.set(a,u)),u.push({onLoad:t,onError:i})}return a}let o=xr("img");function c(){h(),t&&t(this);let u=cr.get(this)||[];for(let d=0;d<u.length;d++){let p=u[d];p.onLoad&&p.onLoad(this)}cr.delete(this),r.manager.itemEnd(e)}function l(u){h(),i&&i(u),xi.remove(`image:${e}`);let d=cr.get(this)||[];for(let p=0;p<d.length;p++){let g=d[p];g.onError&&g.onError(u)}cr.delete(this),r.manager.itemError(e),r.manager.itemEnd(e)}function h(){o.removeEventListener("load",c,!1),o.removeEventListener("error",l,!1)}return o.addEventListener("load",c,!1),o.addEventListener("error",l,!1),e.slice(0,5)!=="data:"&&this.crossOrigin!==void 0&&(o.crossOrigin=this.crossOrigin),xi.add(`image:${e}`,o),r.manager.itemStart(e),o.src=e,o}};var Ls=class extends bi{constructor(e){super(e)}load(e,t,n,i){let r=new jt,a=new yl(this.manager);return a.setCrossOrigin(this.crossOrigin),a.setPath(this.path),a.load(e,function(o){r.image=o,r.needsUpdate=!0,t!==void 0&&t(r)},n,i),r}},Ns=class extends ft{constructor(e,t=1){super(),this.isLight=!0,this.type="Light",this.color=new Me(e),this.intensity=t}copy(e,t){return super.copy(e,t),this.color.copy(e.color),this.intensity=e.intensity,this}toJSON(e){let t=super.toJSON(e);return t.object.color=this.color.getHex(),t.object.intensity=this.intensity,t}},hs=class extends Ns{constructor(e,t,n){super(e,n),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(ft.DEFAULT_UP),this.updateMatrix(),this.groundColor=new Me(t)}copy(e,t){return super.copy(e,t),this.groundColor.copy(e.groundColor),this}toJSON(e){let t=super.toJSON(e);return t.object.groundColor=this.groundColor.getHex(),t}},Mh=new je,uf=new R,df=new R,Cr=class{constructor(e){this.camera=e,this.intensity=1,this.bias=0,this.biasNode=null,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new ne(512,512),this.mapType=bn,this.map=null,this.mapPass=null,this.matrix=new je,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new br,this._frameExtents=new ne(1,1),this._viewportCount=1,this._viewports=[new At(0,0,1,1)]}getViewportCount(){return this._viewportCount}getCamera(){return this.camera}getFrustum(){return this._frustum}updateMatrices(e){let t=this.camera;uf.setFromMatrixPosition(e.matrixWorld),t.position.copy(uf),df.setFromMatrixPosition(e.target.matrixWorld),t.lookAt(df),t.updateMatrixWorld(),this._updateMatrix(t,this.matrix,this._frustum)}_updateMatrix(e,t,n,i){Mh.multiplyMatrices(e.projectionMatrix,e.matrixWorldInverse),n.setFromProjectionMatrix(Mh,e.coordinateSystem,e.reversedDepth);let r=this._frameExtents,a=i?i.z/r.x:1,o=i?i.w/r.y:1,c=i?i.x/r.x:0,l=i?i.y/r.y:0;e.coordinateSystem===gr||e.reversedDepth?t.set(.5*a,0,0,.5*a+c,0,.5*o,0,.5*o+l,0,0,1,0,0,0,0,1):t.set(.5*a,0,0,.5*a+c,0,.5*o,0,.5*o+l,0,0,.5,.5,0,0,0,1),t.multiply(Mh)}getViewport(e){return this._viewports[e]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(e){return this.camera=e.camera.clone(),this.intensity=e.intensity,this.bias=e.bias,this.radius=e.radius,this.autoUpdate=e.autoUpdate,this.needsUpdate=e.needsUpdate,this.normalBias=e.normalBias,this.blurSamples=e.blurSamples,this.mapSize.copy(e.mapSize),this.biasNode=e.biasNode,this}clone(){return new this.constructor().copy(this)}toJSON(){let e={};return e.intensity=this.intensity,e.bias=this.bias,e.normalBias=this.normalBias,e.radius=this.radius,e.blurSamples=this.blurSamples,e.mapSize=this.mapSize.toArray(),e.camera=this.camera.toJSON(!1).object,delete e.camera.matrix,e}},Vo=new R,Ho=new nn,pi=new R,Na=class extends ft{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new je,this.projectionMatrix=new je,this.projectionMatrixInverse=new je,this.coordinateSystem=ni,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(e,t){return super.copy(e,t),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorld.decompose(Vo,Ho,pi),pi.x===1&&pi.y===1&&pi.z===1?this.matrixWorldInverse.copy(this.matrixWorld).invert():this.matrixWorldInverse.compose(Vo,Ho,pi.set(1,1,1)).invert()}updateWorldMatrix(e,t,n=!1){super.updateWorldMatrix(e,t,n),this.matrixWorld.decompose(Vo,Ho,pi),pi.x===1&&pi.y===1&&pi.z===1?this.matrixWorldInverse.copy(this.matrixWorld).invert():this.matrixWorldInverse.compose(Vo,Ho,pi.set(1,1,1)).invert()}clone(){return new this.constructor().copy(this)}},ns=new R,ff=new ne,pf=new ne,zt=class extends Na{constructor(e=50,t=1,n=.1,i=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=n,this.far=i,this.focus=10,this.aspect=t,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){let t=.5*this.getFilmHeight()/e;this.fov=As*2*Math.atan(t),this.updateProjectionMatrix()}getFocalLength(){let e=Math.tan(dr*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return As*2*Math.atan(Math.tan(dr*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(e,t,n){ns.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),t.set(ns.x,ns.y).multiplyScalar(-e/ns.z),ns.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(ns.x,ns.y).multiplyScalar(-e/ns.z)}getViewSize(e,t){return this.getViewBounds(e,ff,pf),t.subVectors(pf,ff)}setViewOffset(e,t,n,i,r,a){this.aspect=e/t,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=i,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=this.near,t=e*Math.tan(dr*.5*this.fov)/this.zoom,n=2*t,i=this.aspect*n,r=-.5*i,a=this.view;if(this.view!==null&&this.view.enabled){let c=a.fullWidth,l=a.fullHeight;r+=a.offsetX*i/c,t-=a.offsetY*n/l,i*=a.width/c,n*=a.height/l}let o=this.filmOffset;o!==0&&(r+=e*o/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+i,t,t-n,e,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.fov=this.fov,t.object.zoom=this.zoom,t.object.near=this.near,t.object.far=this.far,t.object.focus=this.focus,t.object.aspect=this.aspect,this.view!==null&&(t.object.view=Object.assign({},this.view)),t.object.filmGauge=this.filmGauge,t.object.filmOffset=this.filmOffset,t}},Nh=class extends Cr{constructor(){super(new zt(50,1,.5,500)),this.isSpotLightShadow=!0,this.focus=1,this.aspect=1}updateMatrices(e){let t=this.camera,n=As*2*e.angle*this.focus,i=this.mapSize.width/this.mapSize.height*this.aspect,r=e.distance||t.far;(n!==t.fov||i!==t.aspect||r!==t.far)&&(t.fov=n,t.aspect=i,t.far=r,t.updateProjectionMatrix()),super.updateMatrices(e)}copy(e){return super.copy(e),this.focus=e.focus,this.aspect=e.aspect,this}toJSON(){let e=super.toJSON();return e.focus=this.focus,e.aspect=this.aspect,e}},Da=class extends Ns{constructor(e,t,n=0,i=Math.PI/3,r=0,a=2){super(e,t),this.isSpotLight=!0,this.type="SpotLight",this.position.copy(ft.DEFAULT_UP),this.updateMatrix(),this.target=new ft,this.distance=n,this.angle=i,this.penumbra=r,this.decay=a,this.map=null,this.shadow=new Nh}get power(){return this.intensity*Math.PI}set power(e){this.intensity=e/Math.PI}dispose(){super.dispose(),this.shadow.dispose()}copy(e,t){return super.copy(e,t),this.distance=e.distance,this.angle=e.angle,this.penumbra=e.penumbra,this.decay=e.decay,this.target=e.target.clone(),this.map=e.map,this.shadow=e.shadow.clone(),this}toJSON(e){let t=super.toJSON(e);return t.object.distance=this.distance,t.object.angle=this.angle,t.object.decay=this.decay,t.object.penumbra=this.penumbra,t.object.target=this.target.uuid,this.map&&this.map.isTexture&&(t.object.map=this.map.toJSON(e).uuid),t.object.shadow=this.shadow.toJSON(),t}},Dh=class extends Cr{constructor(){super(new zt(90,1,.5,500)),this.isPointLightShadow=!0}},Ln=class extends Ns{constructor(e,t,n=0,i=2){super(e,t),this.isPointLight=!0,this.type="PointLight",this.distance=n,this.decay=i,this.shadow=new Dh}get power(){return this.intensity*4*Math.PI}set power(e){this.intensity=e/(4*Math.PI)}dispose(){super.dispose(),this.shadow.dispose()}copy(e,t){return super.copy(e,t),this.distance=e.distance,this.decay=e.decay,this.shadow=e.shadow.clone(),this}toJSON(e){let t=super.toJSON(e);return t.object.distance=this.distance,t.object.decay=this.decay,t.object.shadow=this.shadow.toJSON(),t}},Ti=class extends Na{constructor(e=-1,t=1,n=1,i=-1,r=.1,a=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=t,this.top=n,this.bottom=i,this.near=r,this.far=a,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,t,n,i,r,a){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=i,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=(this.right-this.left)/(2*this.zoom),t=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,i=(this.top+this.bottom)/2,r=n-e,a=n+e,o=i+t,c=i-t;if(this.view!==null&&this.view.enabled){let l=(this.right-this.left)/this.view.fullWidth/this.zoom,h=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=l*this.view.offsetX,a=r+l*this.view.width,o-=h*this.view.offsetY,c=o-h*this.view.height}this.projectionMatrix.makeOrthographic(r,a,o,c,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.zoom=this.zoom,t.object.left=this.left,t.object.right=this.right,t.object.top=this.top,t.object.bottom=this.bottom,t.object.near=this.near,t.object.far=this.far,this.view!==null&&(t.object.view=Object.assign({},this.view)),t}},Uh=class extends Cr{constructor(){super(new Ti(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}},Nn=class extends Ns{constructor(e,t){super(e,t),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(ft.DEFAULT_UP),this.updateMatrix(),this.target=new ft,this.shadow=new Uh}dispose(){super.dispose(),this.shadow.dispose()}copy(e){return super.copy(e),this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}toJSON(e){let t=super.toJSON(e);return t.object.shadow=this.shadow.toJSON(),t.object.target=this.target.uuid,t}};var Wi=class{static extractUrlBase(e){let t=e.lastIndexOf("/");return t===-1?"./":e.slice(0,t+1)}static resolveURL(e,t){return typeof e!="string"||e===""?"":(/^https?:\/\//i.test(t)&&/^\//.test(e)&&(t=t.replace(/(^https?:\/\/[^\/]+).*/i,"$1")),/^(https?:)?\/\//i.test(e)||/^data:.*,.*$/i.test(e)||/^blob:.*$/i.test(e)?e:t+e)}};var Sh=new WeakMap,Ua=class extends bi{constructor(e){super(e),this.isImageBitmapLoader=!0,typeof createImageBitmap>"u"&&Le("ImageBitmapLoader: createImageBitmap() not supported."),typeof fetch>"u"&&Le("ImageBitmapLoader: fetch() not supported."),this.options={premultiplyAlpha:"none"},this._abortController=new AbortController}setOptions(e){return this.options=e,this}load(e,t,n,i){e===void 0&&(e=""),this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=this,a=xi.get(`image-bitmap:${e}`);if(a!==void 0){if(r.manager.itemStart(e),a.then){a.then(l=>{Sh.has(a)===!0?(i&&i(Sh.get(a)),r.manager.itemError(e),r.manager.itemEnd(e)):(t&&t(l),r.manager.itemEnd(e))});return}setTimeout(function(){t&&t(a),r.manager.itemEnd(e)},0);return}let o={};o.credentials=this.crossOrigin==="anonymous"?"same-origin":"include",o.headers=this.requestHeader,o.signal=typeof AbortSignal.any=="function"?AbortSignal.any([this._abortController.signal,this.manager.abortController.signal]):this._abortController.signal;let c=fetch(e,o).then(function(l){return l.blob()}).then(function(l){return createImageBitmap(l,Object.assign({},r.options,{colorSpaceConversion:"none"}))}).then(function(l){return xi.add(`image-bitmap:${e}`,l),t&&t(l),r.manager.itemEnd(e),l}).catch(function(l){i&&i(l),Sh.set(c,l),xi.remove(`image-bitmap:${e}`),r.manager.itemError(e),r.manager.itemEnd(e)});xi.add(`image-bitmap:${e}`,c),r.manager.itemStart(e)}abort(){return this._abortController.abort(),this._abortController=new AbortController,this}};var hr=-90,ur=1,vl=class extends ft{constructor(e,t,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;let i=new zt(hr,ur,e,t);i.layers=this.layers,this.add(i);let r=new zt(hr,ur,e,t);r.layers=this.layers,this.add(r);let a=new zt(hr,ur,e,t);a.layers=this.layers,this.add(a);let o=new zt(hr,ur,e,t);o.layers=this.layers,this.add(o);let c=new zt(hr,ur,e,t);c.layers=this.layers,this.add(c);let l=new zt(hr,ur,e,t);l.layers=this.layers,this.add(l)}updateCoordinateSystem(){let e=this.coordinateSystem,t=this.children.concat(),[n,i,r,a,o,c]=t;for(let l of t)this.remove(l);if(e===ni)n.up.set(0,1,0),n.lookAt(1,0,0),i.up.set(0,1,0),i.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),a.up.set(0,0,1),a.lookAt(0,-1,0),o.up.set(0,1,0),o.lookAt(0,0,1),c.up.set(0,1,0),c.lookAt(0,0,-1);else if(e===gr)n.up.set(0,-1,0),n.lookAt(-1,0,0),i.up.set(0,-1,0),i.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),a.up.set(0,0,-1),a.lookAt(0,-1,0),o.up.set(0,-1,0),o.lookAt(0,0,1),c.up.set(0,-1,0),c.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(let l of t)this.add(l),l.updateMatrixWorld()}update(e,t){this.parent===null&&this.updateMatrixWorld();let{renderTarget:n,activeMipmapLevel:i}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());let[r,a,o,c,l,h]=this.children,u=e.getRenderTarget(),d=e.getActiveCubeFace(),p=e.getActiveMipmapLevel(),g=e.xr.enabled;e.xr.enabled=!1;let v=n.texture.generateMipmaps;n.texture.generateMipmaps=!1;let f=!1;e.isWebGLRenderer===!0?f=e.state.buffers.depth.getReversed():f=e.reversedDepthBuffer,e.setRenderTarget(n,0,i),f&&e.autoClear===!1&&e.clearDepth(),e.render(t,r),e.setRenderTarget(n,1,i),f&&e.autoClear===!1&&e.clearDepth(),e.render(t,a),e.setRenderTarget(n,2,i),f&&e.autoClear===!1&&e.clearDepth(),e.render(t,o),e.setRenderTarget(n,3,i),f&&e.autoClear===!1&&e.clearDepth(),e.render(t,c),e.setRenderTarget(n,4,i),f&&e.autoClear===!1&&e.clearDepth(),e.render(t,l),n.texture.generateMipmaps=v,e.setRenderTarget(n,5,i),f&&e.autoClear===!1&&e.clearDepth(),e.render(t,h),e.setRenderTarget(u,d,p),e.xr.enabled=g,n.texture.needsPMREMUpdate=!0}},Ml=class extends zt{constructor(e=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=e}},Fa=class{constructor(){this._previousTime=0,this._currentTime=0,this._startTime=performance.now(),this._delta=0,this._elapsed=0,this._timescale=1,this._document=null,this._pageVisibilityHandler=null}connect(e){this._document=e,e.hidden!==void 0&&(this._pageVisibilityHandler=e0.bind(this),e.addEventListener("visibilitychange",this._pageVisibilityHandler,!1))}disconnect(){this._pageVisibilityHandler!==null&&(this._document.removeEventListener("visibilitychange",this._pageVisibilityHandler),this._pageVisibilityHandler=null),this._document=null}getDelta(){return this._delta/1e3}getElapsed(){return this._elapsed/1e3}getTimescale(){return this._timescale}setTimescale(e){return this._timescale=e,this}reset(){return this._currentTime=performance.now()-this._startTime,this}dispose(){this.disconnect()}update(e){return this._pageVisibilityHandler!==null&&this._document.hidden===!0?this._delta=0:(this._previousTime=this._currentTime,this._currentTime=(e!==void 0?e:performance.now())-this._startTime,this._delta=(this._currentTime-this._previousTime)*this._timescale,this._elapsed+=this._delta),this}};function e0(){this._document.hidden===!1&&this.reset()}var su="\\[\\]\\.:\\/",t0=new RegExp("["+su+"]","g"),ru="[^"+su+"]",n0="[^"+su.replace("\\.","")+"]",i0=/((?:WC+[\/:])*)/.source.replace("WC",ru),s0=/(WCOD+)?/.source.replace("WCOD",n0),r0=/(?:\.(WC+)(?:\[(.+)\])?)?/.source.replace("WC",ru),a0=/\.(WC+)(?:\[(.+)\])?/.source.replace("WC",ru),o0=new RegExp("^"+i0+s0+r0+a0+"$"),l0=["material","materials","bones","map"],Fh=class{constructor(e,t,n){let i=n||Lt.parseTrackName(t);this._targetGroup=e,this._bindings=e.subscribe_(t,i)}getValue(e,t){this.bind();let n=this._targetGroup.nCachedObjects_,i=this._bindings[n];i!==void 0&&i.getValue(e,t)}setValue(e,t){let n=this._bindings;for(let i=this._targetGroup.nCachedObjects_,r=n.length;i!==r;++i)n[i].setValue(e,t)}bind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,n=e.length;t!==n;++t)e[t].bind()}unbind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,n=e.length;t!==n;++t)e[t].unbind()}},Lt=class s{constructor(e,t,n){this.path=t,this.parsedPath=n||s.parseTrackName(t),this.node=s.findNode(e,this.parsedPath.nodeName),this.rootNode=e,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}static create(e,t,n){return e&&e.isAnimationObjectGroup?new s.Composite(e,t,n):new s(e,t,n)}static sanitizeNodeName(e){return e.replace(/\s/g,"_").replace(t0,"")}static parseTrackName(e){let t=o0.exec(e);if(t===null)throw new Error("THREE.PropertyBinding: Cannot parse trackName: "+e);let n={nodeName:t[2],objectName:t[3],objectIndex:t[4],propertyName:t[5],propertyIndex:t[6]},i=n.nodeName&&n.nodeName.lastIndexOf(".");if(i!==void 0&&i!==-1){let r=n.nodeName.substring(i+1);l0.indexOf(r)!==-1&&(n.nodeName=n.nodeName.substring(0,i),n.objectName=r)}if(n.propertyName===null||n.propertyName.length===0)throw new Error("THREE.PropertyBinding: can not parse propertyName from trackName: "+e);return n}static findNode(e,t){if(t===void 0||t===""||t==="."||t===-1||t===e.name||t===e.uuid)return e;if(e.skeleton){let n=e.skeleton.getBoneByName(t);if(n!==void 0)return n}if(e.children){let n=function(r){for(let a=0;a<r.length;a++){let o=r[a];if(o.name===t||o.uuid===t)return o;let c=n(o.children);if(c)return c}return null},i=n(e.children);if(i)return i}return null}_getValue_unavailable(){}_setValue_unavailable(){}_getValue_direct(e,t){e[t]=this.targetObject[this.propertyName]}_getValue_array(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)e[t++]=n[i]}_getValue_arrayElement(e,t){e[t]=this.resolvedProperty[this.propertyIndex]}_getValue_toArray(e,t){this.resolvedProperty.toArray(e,t)}_setValue_direct(e,t){this.targetObject[this.propertyName]=e[t]}_setValue_direct_setNeedsUpdate(e,t){this.targetObject[this.propertyName]=e[t],this.targetObject.needsUpdate=!0}_setValue_direct_setMatrixWorldNeedsUpdate(e,t){this.targetObject[this.propertyName]=e[t],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_array(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=e[t++]}_setValue_array_setNeedsUpdate(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=e[t++];this.targetObject.needsUpdate=!0}_setValue_array_setMatrixWorldNeedsUpdate(e,t){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=e[t++];this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_arrayElement(e,t){this.resolvedProperty[this.propertyIndex]=e[t]}_setValue_arrayElement_setNeedsUpdate(e,t){this.resolvedProperty[this.propertyIndex]=e[t],this.targetObject.needsUpdate=!0}_setValue_arrayElement_setMatrixWorldNeedsUpdate(e,t){this.resolvedProperty[this.propertyIndex]=e[t],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_fromArray(e,t){this.resolvedProperty.fromArray(e,t)}_setValue_fromArray_setNeedsUpdate(e,t){this.resolvedProperty.fromArray(e,t),this.targetObject.needsUpdate=!0}_setValue_fromArray_setMatrixWorldNeedsUpdate(e,t){this.resolvedProperty.fromArray(e,t),this.targetObject.matrixWorldNeedsUpdate=!0}_getValue_unbound(e,t){this.bind(),this.getValue(e,t)}_setValue_unbound(e,t){this.bind(),this.setValue(e,t)}bind(){let e=this.node,t=this.parsedPath,n=t.objectName,i=t.propertyName,r=t.propertyIndex;if(e||(e=s.findNode(this.rootNode,t.nodeName),this.node=e),this.getValue=this._getValue_unavailable,this.setValue=this._setValue_unavailable,!e){Le("PropertyBinding: No target node found for track: "+this.path+".");return}if(n){let l=t.objectIndex;switch(n){case"materials":if(!e.material){He("PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!e.material.materials){He("PropertyBinding: Can not bind to material.materials as node.material does not have a materials array.",this);return}e=e.material.materials;break;case"bones":if(!e.skeleton){He("PropertyBinding: Can not bind to bones as node does not have a skeleton.",this);return}e=e.skeleton.bones;for(let h=0;h<e.length;h++)if(e[h].name===l){l=h;break}break;case"map":if("map"in e){e=e.map;break}if(!e.material){He("PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!e.material.map){He("PropertyBinding: Can not bind to material.map as node.material does not have a map.",this);return}e=e.material.map;break;default:if(e[n]===void 0){He("PropertyBinding: Can not bind to objectName of node undefined.",this);return}e=e[n]}if(l!==void 0){if(e[l]===void 0){He("PropertyBinding: Trying to bind to objectIndex of objectName, but is undefined.",this,e);return}e=e[l]}}let a=e[i];if(a===void 0){let l=t.nodeName;He("PropertyBinding: Trying to update property for track: "+l+"."+i+" but it wasn't found.",e);return}let o=this.Versioning.None;this.targetObject=e,e.isMaterial===!0?o=this.Versioning.NeedsUpdate:e.isObject3D===!0&&(o=this.Versioning.MatrixWorldNeedsUpdate);let c=this.BindingType.Direct;if(r!==void 0){if(i==="morphTargetInfluences"){if(!e.geometry){He("PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.",this);return}if(!e.geometry.morphAttributes){He("PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.morphAttributes.",this);return}e.morphTargetDictionary[r]!==void 0&&(r=e.morphTargetDictionary[r])}c=this.BindingType.ArrayElement,this.resolvedProperty=a,this.propertyIndex=r}else a.fromArray!==void 0&&a.toArray!==void 0?(c=this.BindingType.HasFromToArray,this.resolvedProperty=a):Array.isArray(a)?(c=this.BindingType.EntireArray,this.resolvedProperty=a):this.propertyName=i;this.getValue=this.GetterByBindingType[c],this.setValue=this.SetterByBindingTypeAndVersioning[c][o]}unbind(){this.node=null,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}};Lt.Composite=Fh;Lt.prototype.BindingType={Direct:0,EntireArray:1,ArrayElement:2,HasFromToArray:3};Lt.prototype.Versioning={None:0,NeedsUpdate:1,MatrixWorldNeedsUpdate:2};Lt.prototype.GetterByBindingType=[Lt.prototype._getValue_direct,Lt.prototype._getValue_array,Lt.prototype._getValue_arrayElement,Lt.prototype._getValue_toArray];Lt.prototype.SetterByBindingTypeAndVersioning=[[Lt.prototype._setValue_direct,Lt.prototype._setValue_direct_setNeedsUpdate,Lt.prototype._setValue_direct_setMatrixWorldNeedsUpdate],[Lt.prototype._setValue_array,Lt.prototype._setValue_array_setNeedsUpdate,Lt.prototype._setValue_array_setMatrixWorldNeedsUpdate],[Lt.prototype._setValue_arrayElement,Lt.prototype._setValue_arrayElement_setNeedsUpdate,Lt.prototype._setValue_arrayElement_setMatrixWorldNeedsUpdate],[Lt.prototype._setValue_fromArray,Lt.prototype._setValue_fromArray_setNeedsUpdate,Lt.prototype._setValue_fromArray_setMatrixWorldNeedsUpdate]];var EM=new Float32Array(1);var Oh=class s{static{s.prototype.isMatrix2=!0}constructor(e,t,n,i){this.elements=[1,0,0,1],e!==void 0&&this.set(e,t,n,i)}identity(){return this.set(1,0,0,1),this}fromArray(e,t=0){for(let n=0;n<4;n++)this.elements[n]=e[n+t];return this}set(e,t,n,i){let r=this.elements;return r[0]=e,r[2]=t,r[1]=n,r[3]=i,this}};function au(s,e,t,n){let i=c0(n);switch(t){case Zh:return s*e;case El:return s*e/i.components*i.byteLength;case Cl:return s*e/i.components*i.byteLength;case fs:return s*e*2/i.components*i.byteLength;case Rl:return s*e*2/i.components*i.byteLength;case Jh:return s*e*3/i.components*i.byteLength;case Un:return s*e*4/i.components*i.byteLength;case Il:return s*e*4/i.components*i.byteLength;case Wa:case Xa:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*8;case qa:case Ya:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case Ll:case Dl:return Math.max(s,16)*Math.max(e,8)/4;case Pl:case Nl:return Math.max(s,8)*Math.max(e,8)/2;case Ul:case Fl:case Bl:case kl:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*8;case Ol:case Ka:case zl:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case Gl:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case Vl:return Math.floor((s+4)/5)*Math.floor((e+3)/4)*16;case Hl:return Math.floor((s+4)/5)*Math.floor((e+4)/5)*16;case Wl:return Math.floor((s+5)/6)*Math.floor((e+4)/5)*16;case Xl:return Math.floor((s+5)/6)*Math.floor((e+5)/6)*16;case ql:return Math.floor((s+7)/8)*Math.floor((e+4)/5)*16;case Yl:return Math.floor((s+7)/8)*Math.floor((e+5)/6)*16;case Kl:return Math.floor((s+7)/8)*Math.floor((e+7)/8)*16;case Zl:return Math.floor((s+9)/10)*Math.floor((e+4)/5)*16;case Jl:return Math.floor((s+9)/10)*Math.floor((e+5)/6)*16;case $l:return Math.floor((s+9)/10)*Math.floor((e+7)/8)*16;case jl:return Math.floor((s+9)/10)*Math.floor((e+9)/10)*16;case Ql:return Math.floor((s+11)/12)*Math.floor((e+9)/10)*16;case ec:return Math.floor((s+11)/12)*Math.floor((e+11)/12)*16;case tc:case nc:case ic:return Math.ceil(s/4)*Math.ceil(e/4)*16;case sc:case rc:return Math.ceil(s/4)*Math.ceil(e/4)*8;case Za:case ac:return Math.ceil(s/4)*Math.ceil(e/4)*16}throw new Error(`Unable to determine texture byte length for ${t} format.`)}function c0(s){switch(s){case bn:case Xh:return{byteLength:1,components:1};case Nr:case qh:case an:return{byteLength:2,components:1};case wl:case Al:return{byteLength:2,components:4};case oi:case Tl:case Dn:return{byteLength:4,components:1};case Yh:case Kh:return{byteLength:4,components:3}}throw new Error(`THREE.TextureUtils: Unknown texture type ${s}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"186"}}));typeof window<"u"&&(window.__THREE__?Le("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="186");function Cp(){let s=null,e=!1,t=null,n=null;function i(r,a){n=s.requestAnimationFrame(i),t(r,a)}return{start:function(){e!==!0&&t!==null&&s!==null&&(n=s.requestAnimationFrame(i),e=!0)},stop:function(){s!==null&&s.cancelAnimationFrame(n),e=!1},setAnimationLoop:function(r){t=r},setContext:function(r){s=r}}}function u0(s){let e=new WeakMap;function t(o,c){let l=o.array,h=o.usage,u=l.byteLength,d=s.createBuffer();s.bindBuffer(c,d),s.bufferData(c,l,h),o.onUploadCallback();let p;if(l instanceof Float32Array)p=s.FLOAT;else if(typeof Float16Array<"u"&&l instanceof Float16Array)p=s.HALF_FLOAT;else if(l instanceof Uint16Array)o.isFloat16BufferAttribute?p=s.HALF_FLOAT:p=s.UNSIGNED_SHORT;else if(l instanceof Int16Array)p=s.SHORT;else if(l instanceof Uint32Array)p=s.UNSIGNED_INT;else if(l instanceof Int32Array)p=s.INT;else if(l instanceof Int8Array)p=s.BYTE;else if(l instanceof Uint8Array)p=s.UNSIGNED_BYTE;else if(l instanceof Uint8ClampedArray)p=s.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+l);return{buffer:d,type:p,bytesPerElement:l.BYTES_PER_ELEMENT,version:o.version,size:u}}function n(o,c,l){let h=c.array,u=c.updateRanges;if(s.bindBuffer(l,o),u.length===0)s.bufferSubData(l,0,h);else{u.sort((p,g)=>p.start-g.start);let d=0;for(let p=1;p<u.length;p++){let g=u[d],v=u[p];v.start<=g.start+g.count+1?g.count=Math.max(g.count,v.start+v.count-g.start):(++d,u[d]=v)}u.length=d+1;for(let p=0,g=u.length;p<g;p++){let v=u[p];s.bufferSubData(l,v.start*h.BYTES_PER_ELEMENT,h,v.start,v.count)}c.clearUpdateRanges()}c.onUploadCallback()}function i(o){return o.isInterleavedBufferAttribute&&(o=o.data),e.get(o)}function r(o){o.isInterleavedBufferAttribute&&(o=o.data);let c=e.get(o);c&&(s.deleteBuffer(c.buffer),e.delete(o))}function a(o,c){if(o.isInterleavedBufferAttribute&&(o=o.data),o.isGLBufferAttribute){let h=e.get(o);(!h||h.version<o.version)&&e.set(o,{buffer:o.buffer,type:o.type,bytesPerElement:o.elementSize,version:o.version});return}let l=e.get(o);if(l===void 0)e.set(o,t(o,c));else if(l.version<o.version){if(l.size!==o.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");n(l.buffer,o,c),l.version=o.version}}return{get:i,remove:r,update:a}}var d0=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,f0=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,p0=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,m0=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,g0=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,x0=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,_0=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,y0=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,v0=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec4 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 );
	}
#endif`,M0=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,S0=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,b0=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,T0=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,w0=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,A0=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,E0=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,C0=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,R0=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,I0=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,P0=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#endif`,L0=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#endif`,N0=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec4 vColor;
#endif`,D0=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec4( 1.0 );
#endif
#ifdef USE_COLOR_ALPHA
	vColor *= color;
#elif defined( USE_COLOR )
	vColor.rgb *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.rgb *= instanceColor.rgb;
#endif
#ifdef USE_BATCHING_COLOR
	vColor *= getBatchingColor( getIndirectIndex( gl_DrawID ) );
#endif`,U0=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
#define inverseTransformDirection transformDirectionByInverseViewMatrix
vec3 transformNormalByInverseViewMatrix( in vec3 normal, in mat4 viewMatrix ) {
	return normalize( ( vec4( normal, 0.0 ) * viewMatrix ).xyz );
}
vec3 transformDirectionByInverseViewMatrix( in vec3 dir, in mat4 viewMatrix ) {
	return normalize( ( vec4( dir, 0.0 ) * viewMatrix ).xyz );
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,F0=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,O0=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
#endif`,B0=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,k0=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,z0=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,G0=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,V0="gl_FragColor = linearToOutputTexel( gl_FragColor );",H0=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,W0=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = transformNormalByInverseViewMatrix( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * reflectVec );
		#ifdef ENVMAP_BLENDING_MULTIPLY
			outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
		#elif defined( ENVMAP_BLENDING_MIX )
			outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
		#elif defined( ENVMAP_BLENDING_ADD )
			outgoingLight += envColor.xyz * specularStrength * reflectivity;
		#endif
	#endif
#endif`,X0=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
#endif`,q0=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,Y0=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,K0=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = transformNormalByInverseViewMatrix( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,Z0=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,J0=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,$0=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,j0=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,Q0=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,ex=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,tx=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,nx=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,ix=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = transformNormalByInverseViewMatrix( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_SUN_LIGHTS > 0
	struct SunLight {
		vec3 direction;
		vec3 color;
	};
	uniform SunLight sunLights[ NUM_SUN_LIGHTS ];
	void getSunLightInfo( const in SunLight sunLight, out IncidentLight light ) {
		light.color = sunLight.color;
		light.direction = sunLight.direction;
		light.visible = true;
	}
#endif
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif
#include <lightprobes_pars_fragment>`,sx=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = transformNormalByInverseViewMatrix( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, pow4( roughness ) ) );
			reflectVec = transformDirectionByInverseViewMatrix( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_RETROREFLECTION
		vec3 getIBLRetroRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 retroVec = normalize( mix( viewDir, normal, pow4( roughness ) ) );
				retroVec = transformDirectionByInverseViewMatrix( retroVec, viewMatrix );
				vec4 envMapColor = textureCubeUV( envMap, envMapRotation * retroVec, roughness );
				return envMapColor.rgb * envMapIntensity;
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
		#ifdef USE_RETROREFLECTION
			vec3 getIBLAnisotropyRetroRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
				#ifdef ENVMAP_TYPE_CUBE_UV
					vec3 bentNormal = cross( bitangent, viewDir );
					bentNormal = normalize( cross( bentNormal, bitangent ) );
					bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
					return getIBLRetroRadiance( viewDir, bentNormal, roughness );
				#else
					return vec3( 0.0 );
				#endif
			}
		#endif
	#endif
#endif`,rx=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,ax=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,ox=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,lx=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,cx=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.diffuseContribution = diffuseColor.rgb * ( 1.0 - metalnessFactor );
material.metalness = metalnessFactor;
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor;
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = vec3( 0.04 );
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_RETROREFLECTION
	material.retroreflectivity = retroreflectivity;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.0001, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,hx=`uniform sampler2D dfgLUT;
struct PhysicalMaterial {
	vec3 diffuseColor;
	vec3 diffuseContribution;
	vec3 specularColor;
	vec3 specularColorBlended;
	float roughness;
	float metalness;
	float specularF90;
	float dispersion;
	vec2 dfg;
	vec3 multiScatteringCompensation;
	#ifdef USE_RETROREFLECTION
		float retroreflectivity;
	#endif
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0Dielectric;
		vec3 iridescenceF0Metallic;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		return 0.5 / max( gv + gl, EPSILON );
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColorBlended;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transpose( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float rInv = 1.0 / ( roughness + 0.1 );
	float a = -1.9362 + 1.0678 * roughness + 0.4573 * r2 - 0.8469 * rInv;
	float b = -0.6014 + 0.5538 * roughness - 0.4670 * r2 - 0.1255 * rInv;
	float DG = exp( a * dotNV + b );
	return saturate( DG );
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec2 fab, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec2 fab, const in vec3 specularColor, const in float specularF90, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColorBlended * t2.x + ( material.specularF90 - material.specularColorBlended ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseContribution * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
		#ifdef USE_CLEARCOAT
			vec3 Ncc = geometryClearcoatNormal;
			vec2 uvClearcoat = LTC_Uv( Ncc, viewDir, material.clearcoatRoughness );
			vec4 t1Clearcoat = texture2D( ltc_1, uvClearcoat );
			vec4 t2Clearcoat = texture2D( ltc_2, uvClearcoat );
			mat3 mInvClearcoat = mat3(
				vec3( t1Clearcoat.x, 0, t1Clearcoat.y ),
				vec3(             0, 1,             0 ),
				vec3( t1Clearcoat.z, 0, t1Clearcoat.w )
			);
			vec3 fresnelClearcoat = material.clearcoatF0 * t2Clearcoat.x + ( material.clearcoatF90 - material.clearcoatF0 ) * t2Clearcoat.y;
			clearcoatSpecularDirect += lightColor * fresnelClearcoat * LTC_Evaluate( Ncc, viewDir, position, mInvClearcoat, rectCoords );
		#endif
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
 
 		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
 
 		float sheenAlbedoV = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
 		float sheenAlbedoL = IBLSheenBRDF( geometryNormal, directLight.direction, material.sheenRoughness );
 
 		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * max( sheenAlbedoV, sheenAlbedoL );
 
 		irradiance *= sheenEnergyComp;
 
 	#endif
	vec3 specularBRDF = BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	#ifdef USE_RETROREFLECTION
		vec3 retroViewDir = reflect( - geometryViewDir, geometryNormal );
		vec3 retroSpecularBRDF = BRDF_GGX( directLight.direction, retroViewDir, geometryNormal, material );
		specularBRDF = mix( specularBRDF, retroSpecularBRDF, saturate( material.retroreflectivity ) );
	#endif
	reflectedLight.directSpecular += irradiance * specularBRDF * material.multiScatteringCompensation;
	vec3 halfDir = normalize( directLight.direction + geometryViewDir );
	float dotVH = saturate( dot( geometryViewDir, halfDir ) );
	vec3 F = F_Schlick( material.specularColor, material.specularF90, dotVH );
	#ifdef USE_RETROREFLECTION
		vec3 retroHalfDir = normalize( directLight.direction + retroViewDir );
		float dotRetroVH = saturate( dot( retroViewDir, retroHalfDir ) );
		vec3 retroF = F_Schlick( material.specularColor, material.specularF90, dotRetroVH );
		F = mix( F, retroF, saturate( material.retroreflectivity ) );
	#endif
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - F );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( material.dfg, material.specularColor, material.specularF90, material.iridescence, material.iridescenceF0Dielectric, singleScattering, multiScattering );
	#else
		computeMultiscattering( material.dfg, material.specularColor, material.specularF90, singleScattering, multiScattering );
	#endif
	vec3 diffuse = irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - singleScattering - multiScattering );
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		sheenSpecularIndirect += irradiance * material.sheenColor * sheenAlbedo * RECIPROCAL_PI;
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		diffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectDiffuse += diffuse;
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness ) * RECIPROCAL_PI;
 	#endif
	vec3 singleScatteringDielectric = vec3( 0.0 );
	vec3 multiScatteringDielectric = vec3( 0.0 );
	vec3 singleScatteringMetallic = vec3( 0.0 );
	vec3 multiScatteringMetallic = vec3( 0.0 );
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( material.dfg, material.specularColor, material.specularF90, material.iridescence, material.iridescenceF0Dielectric, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscatteringIridescence( material.dfg, material.diffuseColor, material.specularF90, material.iridescence, material.iridescenceF0Metallic, singleScatteringMetallic, multiScatteringMetallic );
	#else
		computeMultiscattering( material.dfg, material.specularColor, material.specularF90, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscattering( material.dfg, material.diffuseColor, material.specularF90, singleScatteringMetallic, multiScatteringMetallic );
	#endif
	vec3 singleScattering = mix( singleScatteringDielectric, singleScatteringMetallic, material.metalness );
	vec3 multiScattering = mix( multiScatteringDielectric, multiScatteringMetallic, material.metalness );
	vec3 totalScatteringDielectric = singleScatteringDielectric + multiScatteringDielectric;
	vec3 diffuse = material.diffuseContribution * ( 1.0 - totalScatteringDielectric );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	vec3 indirectSpecular = radiance * singleScattering;
	indirectSpecular += multiScattering * cosineWeightedIrradiance;
	vec3 indirectDiffuse = diffuse * cosineWeightedIrradiance;
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		indirectSpecular *= sheenEnergyComp;
		indirectDiffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectSpecular += indirectSpecular;
	reflectedLight.indirectDiffuse += indirectDiffuse;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,ux=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		vec3 iridescenceFresnelDielectric = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		vec3 iridescenceFresnelMetallic = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.diffuseColor );
		material.iridescenceFresnel = mix( iridescenceFresnelDielectric, iridescenceFresnelMetallic, material.metalness );
		material.iridescenceF0Dielectric = Schlick_to_F0( iridescenceFresnelDielectric, 1.0, dotNVi );
		material.iridescenceF0Metallic = Schlick_to_F0( iridescenceFresnelMetallic, 1.0, dotNVi );
	}
#endif
#ifdef STANDARD
	float dotNVms = saturate( dot( geometryNormal, geometryViewDir ) );
	material.dfg = texture2D( dfgLUT, vec2( material.roughness, dotNVms ) ).rg;
	#if ( NUM_SUN_LIGHTS > 0 || NUM_DIR_LIGHTS > 0 || NUM_POINT_LIGHTS > 0 || NUM_SPOT_LIGHTS > 0 )
		float EssMs = material.dfg.x + material.dfg.y;
		material.multiScatteringCompensation = 1.0 + material.specularColorBlended * ( 1.0 / EssMs - 1.0 );
	#endif
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SUN_LIGHTS > 0 ) && defined( RE_Direct )
	SunLight sunLight;
	#if defined( USE_SHADOWMAP ) && NUM_SUN_LIGHT_SHADOWS > 0
	SunLightShadow sunLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SUN_LIGHTS; i ++ ) {
		sunLight = sunLights[ i ];
		getSunLightInfo( sunLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SUN_LIGHT_SHADOWS )
		sunLightShadow = sunLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getSunShadow( sunShadowMap[ i ], sunLightShadow, UNROLLED_LOOP_INDEX ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
	#ifdef USE_LIGHT_PROBES_GRID
		vec3 probeWorldPos = ( ( vec4( geometryPosition, 1.0 ) - viewMatrix[ 3 ] ) * viewMatrix ).xyz;
		vec3 probeWorldNormal = transformNormalByInverseViewMatrix( geometryNormal, viewMatrix );
		irradiance += getLightProbeGridIrradiance( probeWorldPos, probeWorldNormal );
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,dx=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )
		#if defined( STANDARD ) || defined( LAMBERT ) || defined( PHONG )
			iblIrradiance += getIBLIrradiance( geometryNormal );
		#endif
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		vec3 iblRadiance = getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		vec3 iblRadiance = getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_RETROREFLECTION
		#ifdef USE_ANISOTROPY
			vec3 retroIBLRadiance = getIBLAnisotropyRetroRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
		#else
			vec3 retroIBLRadiance = getIBLRetroRadiance( geometryViewDir, geometryNormal, material.roughness );
		#endif
		iblRadiance = mix( iblRadiance, retroIBLRadiance, saturate( material.retroreflectivity ) );
	#endif
	radiance += iblRadiance;
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,fx=`#if defined( RE_IndirectDiffuse )
	#if defined( LAMBERT ) || defined( PHONG )
		irradiance += iblIrradiance;
	#endif
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,px=`#ifdef USE_LIGHT_PROBES_GRID
uniform highp sampler3D probesSH;
uniform vec3 probesMin;
uniform vec3 probesMax;
uniform vec3 probesResolution;
vec3 getLightProbeGridIrradiance( vec3 worldPos, vec3 worldNormal ) {
	vec3 res = probesResolution;
	vec3 gridRange = probesMax - probesMin;
	vec3 resMinusOne = res - 1.0;
	vec3 probeSpacing = gridRange / resMinusOne;
	vec3 samplePos = worldPos + worldNormal * probeSpacing * 0.5;
	vec3 uvw = clamp( ( samplePos - probesMin ) / gridRange, 0.0, 1.0 );
	uvw = uvw * resMinusOne / res + 0.5 / res;
	float nz          = res.z;
	float paddedSlices = nz + 2.0;
	float atlasDepth  = 7.0 * paddedSlices;
	float uvZBase     = uvw.z * nz + 1.0;
	vec4 s0 = texture( probesSH, vec3( uvw.xy, ( uvZBase                       ) / atlasDepth ) );
	vec4 s1 = texture( probesSH, vec3( uvw.xy, ( uvZBase +       paddedSlices   ) / atlasDepth ) );
	vec4 s2 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 2.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s3 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 3.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s4 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 4.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s5 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 5.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s6 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 6.0 * paddedSlices   ) / atlasDepth ) );
	vec3 c0 = s0.xyz;
	vec3 c1 = vec3( s0.w, s1.xy );
	vec3 c2 = vec3( s1.zw, s2.x );
	vec3 c3 = s2.yzw;
	vec3 c4 = s3.xyz;
	vec3 c5 = vec3( s3.w, s4.xy );
	vec3 c6 = vec3( s4.zw, s5.x );
	vec3 c7 = s5.yzw;
	vec3 c8 = s6.xyz;
	float x = worldNormal.x, y = worldNormal.y, z = worldNormal.z;
	vec3 result = c0 * 0.886227;
	result += c1 * 2.0 * 0.511664 * y;
	result += c2 * 2.0 * 0.511664 * z;
	result += c3 * 2.0 * 0.511664 * x;
	result += c4 * 2.0 * 0.429043 * x * y;
	result += c5 * 2.0 * 0.429043 * y * z;
	result += c6 * ( 0.743125 * z * z - 0.247708 );
	result += c7 * 2.0 * 0.429043 * x * z;
	result += c8 * 0.429043 * ( x * x - y * y );
	return max( result, vec3( 0.0 ) );
}
#endif`,mx=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,gx=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,xx=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,_x=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,yx=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,vx=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Mx=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,Sx=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,bx=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,Tx=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,wx=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,Ax=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,Ex=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Cx=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,Rx=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Ix=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#ifdef DOUBLE_SIDED
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#ifdef DOUBLE_SIDED
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,Px=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#if defined( USE_PACKED_NORMALMAP )
		mapN = vec3( mapN.xy, sqrt( saturate( 1.0 - dot( mapN.xy, mapN.xy ) ) ) );
	#endif
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,Lx=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Nx=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Dx=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
		#ifdef FLIP_SIDED
			vBitangent = - vBitangent;
		#endif
	#endif
#endif`,Ux=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,Fx=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,Ox=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,Bx=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,kx=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,zx=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,Gx=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	#ifdef USE_REVERSED_DEPTH_BUFFER
	
		return depth * ( far - near ) - far;
	#else
		return depth * ( near - far ) - near;
	#endif
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	
	#ifdef USE_REVERSED_DEPTH_BUFFER
		return ( near * far ) / ( ( near - far ) * depth - near );
	#else
		return ( near * far ) / ( ( far - near ) * depth - far );
	#endif
}`,Vx=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Hx=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,Wx=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,Xx=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,qx=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Yx=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Kx=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_SUN_LIGHT_SHADOWS > 0
		#define SUN_LIGHT_CASCADES 2
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow sunShadowMap[ NUM_SUN_LIGHT_SHADOWS ];
		#else
			uniform sampler2D sunShadowMap[ NUM_SUN_LIGHT_SHADOWS ];
		#endif
		uniform mat4 sunShadowMatrix[ NUM_SUN_LIGHT_SHADOWS * SUN_LIGHT_CASCADES ];
		uniform vec4 sunShadowCascade[ NUM_SUN_LIGHT_SHADOWS * SUN_LIGHT_CASCADES ];
		varying vec4 vSunShadowWorldPosition;
		varying vec3 vSunShadowWorldNormal;
		struct SunLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SunLightShadow sunLightShadows[ NUM_SUN_LIGHT_SHADOWS ];
	#endif
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#else
			uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#endif
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#else
			uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#endif
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform samplerCubeShadow pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#elif defined( SHADOWMAP_TYPE_BASIC )
			uniform samplerCube pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#endif
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float interleavedGradientNoise( vec2 position ) {
			return fract( 52.9829189 * fract( dot( position, vec2( 0.06711056, 0.00583715 ) ) ) );
		}
		vec2 vogelDiskSample( int sampleIndex, int samplesCount, float phi ) {
			const float goldenAngle = 2.399963229728653;
			float r = sqrt( ( float( sampleIndex ) + 0.5 ) / float( samplesCount ) );
			float theta = float( sampleIndex ) * goldenAngle + phi;
			return vec2( cos( theta ), sin( theta ) ) * r;
		}
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float getShadow( sampler2DShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
				float radius = shadowRadius * texelSize.x;
				float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;
				shadow = (
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 0, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 1, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 2, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 3, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 4, 5, phi ) * radius, shadowCoord.z ) )
				) * 0.2;
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#elif defined( SHADOWMAP_TYPE_VSM )
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadowCoord.z -= shadowBias;
			#else
				shadowCoord.z += shadowBias;
			#endif
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 distribution = texture2D( shadowMap, shadowCoord.xy ).rg;
				float mean = distribution.x;
				float variance = distribution.y * distribution.y;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					float hard_shadow = step( mean, shadowCoord.z );
				#else
					float hard_shadow = step( shadowCoord.z, mean );
				#endif
				
				if ( hard_shadow == 1.0 ) {
					shadow = 1.0;
				} else {
					variance = max( variance, 0.0000001 );
					float d = shadowCoord.z - mean;
					float p_max = variance / ( variance + d * d );
					p_max = clamp( ( p_max - 0.3 ) / 0.65, 0.0, 1.0 );
					shadow = max( hard_shadow, p_max );
				}
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#else
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadowCoord.z -= shadowBias;
			#else
				shadowCoord.z += shadowBias;
			#endif
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				float depth = texture2D( shadowMap, shadowCoord.xy ).r;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					shadow = step( depth, shadowCoord.z );
				#else
					shadow = step( shadowCoord.z, depth );
				#endif
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#endif
	#if NUM_SUN_LIGHT_SHADOWS > 0
		float getSunShadow(
			#if defined( SHADOWMAP_TYPE_PCF )
				sampler2DShadow shadowMap,
			#else
				sampler2D shadowMap,
			#endif
			SunLightShadow sunLightShadow,
			int shadowIndex
		) {
			vec4 shadowWorldPosition = vec4( vSunShadowWorldPosition.xyz + vSunShadowWorldNormal * sunLightShadow.shadowNormalBias, 1.0 );
			float viewDepth = vSunShadowWorldPosition.w;
			int cascadeOffset = shadowIndex * SUN_LIGHT_CASCADES;
			float shadow = 1.0;
			for ( int i = SUN_LIGHT_CASCADES - 1; i >= 0; i -- ) {
				vec4 cascade = sunShadowCascade[ cascadeOffset + i ];
				if ( viewDepth >= cascade.x && viewDepth < cascade.y ) {
					float cascadeShadow = getShadow(
						shadowMap,
						sunLightShadow.shadowMapSize,
						sunLightShadow.shadowIntensity,
						sunLightShadow.shadowBias,
						sunLightShadow.shadowRadius,
						sunShadowMatrix[ cascadeOffset + i ] * shadowWorldPosition
					);
					shadow = mix( cascadeShadow, shadow, smoothstep( cascade.z, cascade.y, viewDepth ) );
				}
			}
			return shadow;
		}
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	#if defined( SHADOWMAP_TYPE_PCF )
	float getPointShadow( samplerCubeShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 bd3D = normalize( lightToPosition );
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			#ifdef USE_REVERSED_DEPTH_BUFFER
				float dp = ( shadowCameraNear * ( shadowCameraFar - viewSpaceZ ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp -= shadowBias;
			#else
				float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp += shadowBias;
			#endif
			float texelSize = shadowRadius / shadowMapSize.x;
			vec3 absDir = abs( bd3D );
			vec3 tangent = absDir.x > absDir.z ? vec3( 0.0, 1.0, 0.0 ) : vec3( 1.0, 0.0, 0.0 );
			tangent = normalize( cross( bd3D, tangent ) );
			vec3 bitangent = cross( bd3D, tangent );
			float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;
			vec2 sample0 = vogelDiskSample( 0, 5, phi );
			vec2 sample1 = vogelDiskSample( 1, 5, phi );
			vec2 sample2 = vogelDiskSample( 2, 5, phi );
			vec2 sample3 = vogelDiskSample( 3, 5, phi );
			vec2 sample4 = vogelDiskSample( 4, 5, phi );
			shadow = (
				texture( shadowMap, vec4( bd3D + ( tangent * sample0.x + bitangent * sample0.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample1.x + bitangent * sample1.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample2.x + bitangent * sample2.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample3.x + bitangent * sample3.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample4.x + bitangent * sample4.y ) * texelSize, dp ) )
			) * 0.2;
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#elif defined( SHADOWMAP_TYPE_BASIC )
	float getPointShadow( samplerCube shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			float depth = textureCube( shadowMap, bd3D ).r;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				depth = 1.0 - depth;
			#endif
			shadow = step( dp, depth );
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#endif
	#endif
#endif`,Zx=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_SUN_LIGHT_SHADOWS > 0
		varying vec4 vSunShadowWorldPosition;
		varying vec3 vSunShadowWorldNormal;
	#endif
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,Jx=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_SUN_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	#ifdef HAS_NORMAL
		vec3 shadowWorldNormal = transformNormalByInverseViewMatrix( transformedNormal, viewMatrix );
	#else
		vec3 shadowWorldNormal = vec3( 0.0 );
	#endif
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_SUN_LIGHT_SHADOWS > 0
		vSunShadowWorldPosition = vec4( worldPosition.xyz, - mvPosition.z );
		vSunShadowWorldNormal = shadowWorldNormal;
	#endif
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,$x=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_SUN_LIGHT_SHADOWS > 0
	SunLightShadow sunLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SUN_LIGHT_SHADOWS; i ++ ) {
		sunLight = sunLightShadows[ i ];
		shadow *= receiveShadow ? getSunShadow( sunShadowMap[ i ], sunLight, UNROLLED_LOOP_INDEX ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0 && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,jx=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,Qx=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,e_=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,t_=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,n_=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,i_=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,s_=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,r_=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,a_=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = transformNormalByInverseViewMatrix( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseContribution, material.specularColorBlended, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,o_=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,l_=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,c_=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,h_=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,u_=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`,d_=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,f_=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,p_=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,m_=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vWorldDirection );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,g_=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,x_=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,__=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,y_=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,v_=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,M_=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = vec4( dist, 0.0, 0.0, 1.0 );
}`,S_=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,b_=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,T_=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,w_=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,A_=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,E_=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,C_=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,R_=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,I_=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,P_=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,L_=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,N_=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( normalize( normal ) * 0.5 + 0.5, diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,D_=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,U_=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,F_=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,O_=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_RETROREFLECTION
	uniform float retroreflectivity;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
 
		outgoingLight = outgoingLight + sheenSpecularDirect + sheenSpecularIndirect;
 
 	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,B_=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,k_=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,z_=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,G_=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,V_=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,H_=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,W_=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,X_=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,at={alphahash_fragment:d0,alphahash_pars_fragment:f0,alphamap_fragment:p0,alphamap_pars_fragment:m0,alphatest_fragment:g0,alphatest_pars_fragment:x0,aomap_fragment:_0,aomap_pars_fragment:y0,batching_pars_vertex:v0,batching_vertex:M0,begin_vertex:S0,beginnormal_vertex:b0,bsdfs:T0,iridescence_fragment:w0,bumpmap_pars_fragment:A0,clipping_planes_fragment:E0,clipping_planes_pars_fragment:C0,clipping_planes_pars_vertex:R0,clipping_planes_vertex:I0,color_fragment:P0,color_pars_fragment:L0,color_pars_vertex:N0,color_vertex:D0,common:U0,cube_uv_reflection_fragment:F0,defaultnormal_vertex:O0,displacementmap_pars_vertex:B0,displacementmap_vertex:k0,emissivemap_fragment:z0,emissivemap_pars_fragment:G0,colorspace_fragment:V0,colorspace_pars_fragment:H0,envmap_fragment:W0,envmap_common_pars_fragment:X0,envmap_pars_fragment:q0,envmap_pars_vertex:Y0,envmap_physical_pars_fragment:sx,envmap_vertex:K0,fog_vertex:Z0,fog_pars_vertex:J0,fog_fragment:$0,fog_pars_fragment:j0,gradientmap_pars_fragment:Q0,lightmap_pars_fragment:ex,lights_lambert_fragment:tx,lights_lambert_pars_fragment:nx,lights_pars_begin:ix,lights_toon_fragment:rx,lights_toon_pars_fragment:ax,lights_phong_fragment:ox,lights_phong_pars_fragment:lx,lights_physical_fragment:cx,lights_physical_pars_fragment:hx,lights_fragment_begin:ux,lights_fragment_maps:dx,lights_fragment_end:fx,lightprobes_pars_fragment:px,logdepthbuf_fragment:mx,logdepthbuf_pars_fragment:gx,logdepthbuf_pars_vertex:xx,logdepthbuf_vertex:_x,map_fragment:yx,map_pars_fragment:vx,map_particle_fragment:Mx,map_particle_pars_fragment:Sx,metalnessmap_fragment:bx,metalnessmap_pars_fragment:Tx,morphinstance_vertex:wx,morphcolor_vertex:Ax,morphnormal_vertex:Ex,morphtarget_pars_vertex:Cx,morphtarget_vertex:Rx,normal_fragment_begin:Ix,normal_fragment_maps:Px,normal_pars_fragment:Lx,normal_pars_vertex:Nx,normal_vertex:Dx,normalmap_pars_fragment:Ux,clearcoat_normal_fragment_begin:Fx,clearcoat_normal_fragment_maps:Ox,clearcoat_pars_fragment:Bx,iridescence_pars_fragment:kx,opaque_fragment:zx,packing:Gx,premultiplied_alpha_fragment:Vx,project_vertex:Hx,dithering_fragment:Wx,dithering_pars_fragment:Xx,roughnessmap_fragment:qx,roughnessmap_pars_fragment:Yx,shadowmap_pars_fragment:Kx,shadowmap_pars_vertex:Zx,shadowmap_vertex:Jx,shadowmask_pars_fragment:$x,skinbase_vertex:jx,skinning_pars_vertex:Qx,skinning_vertex:e_,skinnormal_vertex:t_,specularmap_fragment:n_,specularmap_pars_fragment:i_,tonemapping_fragment:s_,tonemapping_pars_fragment:r_,transmission_fragment:a_,transmission_pars_fragment:o_,uv_pars_fragment:l_,uv_pars_vertex:c_,uv_vertex:h_,worldpos_vertex:u_,background_vert:d_,background_frag:f_,backgroundCube_vert:p_,backgroundCube_frag:m_,cube_vert:g_,cube_frag:x_,depth_vert:__,depth_frag:y_,distance_vert:v_,distance_frag:M_,equirect_vert:S_,equirect_frag:b_,linedashed_vert:T_,linedashed_frag:w_,meshbasic_vert:A_,meshbasic_frag:E_,meshlambert_vert:C_,meshlambert_frag:R_,meshmatcap_vert:I_,meshmatcap_frag:P_,meshnormal_vert:L_,meshnormal_frag:N_,meshphong_vert:D_,meshphong_frag:U_,meshphysical_vert:F_,meshphysical_frag:O_,meshtoon_vert:B_,meshtoon_frag:k_,points_vert:z_,points_frag:G_,shadow_vert:V_,shadow_frag:H_,sprite_vert:W_,sprite_frag:X_},xe={common:{diffuse:{value:new Me(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new Ze},alphaMap:{value:null},alphaMapTransform:{value:new Ze},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new Ze}},envmap:{envMap:{value:null},envMapRotation:{value:new Ze},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98},dfgLUT:{value:null}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new Ze}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new Ze}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new Ze},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new Ze},normalScale:{value:new ne(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new Ze},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new Ze}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new Ze}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new Ze}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new Me(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},sunLights:{value:[],properties:{direction:{},color:{}}},sunLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},sunShadowMatrix:{value:[]},sunShadowCascade:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null},probesSH:{value:null},probesMin:{value:new R},probesMax:{value:new R},probesResolution:{value:new R}},points:{diffuse:{value:new Me(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new Ze},alphaTest:{value:0},uvTransform:{value:new Ze}},sprite:{diffuse:{value:new Me(16777215)},opacity:{value:1},center:{value:new ne(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new Ze},alphaMap:{value:null},alphaMapTransform:{value:new Ze},alphaTest:{value:0}}},Ei={basic:{uniforms:dn([xe.common,xe.specularmap,xe.envmap,xe.aomap,xe.lightmap,xe.fog]),vertexShader:at.meshbasic_vert,fragmentShader:at.meshbasic_frag},lambert:{uniforms:dn([xe.common,xe.specularmap,xe.envmap,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.fog,xe.lights,{emissive:{value:new Me(0)},envMapIntensity:{value:1}}]),vertexShader:at.meshlambert_vert,fragmentShader:at.meshlambert_frag},phong:{uniforms:dn([xe.common,xe.specularmap,xe.envmap,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.fog,xe.lights,{emissive:{value:new Me(0)},specular:{value:new Me(1118481)},shininess:{value:30},envMapIntensity:{value:1}}]),vertexShader:at.meshphong_vert,fragmentShader:at.meshphong_frag},standard:{uniforms:dn([xe.common,xe.envmap,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.roughnessmap,xe.metalnessmap,xe.fog,xe.lights,{emissive:{value:new Me(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:at.meshphysical_vert,fragmentShader:at.meshphysical_frag},toon:{uniforms:dn([xe.common,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.gradientmap,xe.fog,xe.lights,{emissive:{value:new Me(0)}}]),vertexShader:at.meshtoon_vert,fragmentShader:at.meshtoon_frag},matcap:{uniforms:dn([xe.common,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.fog,{matcap:{value:null}}]),vertexShader:at.meshmatcap_vert,fragmentShader:at.meshmatcap_frag},points:{uniforms:dn([xe.points,xe.fog]),vertexShader:at.points_vert,fragmentShader:at.points_frag},dashed:{uniforms:dn([xe.common,xe.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:at.linedashed_vert,fragmentShader:at.linedashed_frag},depth:{uniforms:dn([xe.common,xe.displacementmap]),vertexShader:at.depth_vert,fragmentShader:at.depth_frag},normal:{uniforms:dn([xe.common,xe.bumpmap,xe.normalmap,xe.displacementmap,{opacity:{value:1}}]),vertexShader:at.meshnormal_vert,fragmentShader:at.meshnormal_frag},sprite:{uniforms:dn([xe.sprite,xe.fog]),vertexShader:at.sprite_vert,fragmentShader:at.sprite_frag},background:{uniforms:{uvTransform:{value:new Ze},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:at.background_vert,fragmentShader:at.background_frag},backgroundCube:{uniforms:{envMap:{value:null},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new Ze}},vertexShader:at.backgroundCube_vert,fragmentShader:at.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:at.cube_vert,fragmentShader:at.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:at.equirect_vert,fragmentShader:at.equirect_frag},distance:{uniforms:dn([xe.common,xe.displacementmap,{referencePosition:{value:new R},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:at.distance_vert,fragmentShader:at.distance_frag},shadow:{uniforms:dn([xe.lights,xe.fog,{color:{value:new Me(0)},opacity:{value:1}}]),vertexShader:at.shadow_vert,fragmentShader:at.shadow_frag}};Ei.physical={uniforms:dn([Ei.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new Ze},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new Ze},clearcoatNormalScale:{value:new ne(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new Ze},dispersion:{value:0},retroreflectivity:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new Ze},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new Ze},sheen:{value:0},sheenColor:{value:new Me(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new Ze},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new Ze},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new Ze},transmissionSamplerSize:{value:new ne},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new Ze},attenuationDistance:{value:0},attenuationColor:{value:new Me(0)},specularColor:{value:new Me(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new Ze},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new Ze},anisotropyVector:{value:new ne},anisotropyMap:{value:null},anisotropyMapTransform:{value:new Ze}}]),vertexShader:at.meshphysical_vert,fragmentShader:at.meshphysical_frag};var hc={r:0,b:0,g:0},q_=new je,Rp=new Ze;Rp.set(-1,0,0,0,1,0,0,0,1);function Y_(s,e,t,n,i,r){let a=new Me(0),o=i===!0?0:1,c,l,h=null,u=0,d=null;function p(_){let b=_.isScene===!0?_.background:null;if(b&&b.isTexture){let x=_.backgroundBlurriness>0;b=e.get(b,x)}return b}function g(_){let b=!1,x=p(_);x===null?f(a,o):x&&x.isColor&&(f(x,1),b=!0);let T=s.xr.getEnvironmentBlendMode();T==="additive"?t.buffers.color.setClear(0,0,0,1,r):T==="alpha-blend"&&t.buffers.color.setClear(0,0,0,0,r),(s.autoClear||b)&&(t.buffers.depth.setTest(!0),t.buffers.depth.setMask(!0),t.buffers.color.setMask(!0),s.clear(s.autoClearColor,s.autoClearDepth,s.autoClearStencil))}function v(_,b){let x=p(b);x&&(x.isCubeTexture||x.mapping===Ha)?(l===void 0&&(l=new Ee(new Mn(1,1,1),new Bt({name:"BackgroundCubeMaterial",uniforms:ks(Ei.backgroundCube.uniforms),vertexShader:Ei.backgroundCube.vertexShader,fragmentShader:Ei.backgroundCube.fragmentShader,side:qt,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),l.geometry.deleteAttribute("normal"),l.geometry.deleteAttribute("uv"),l.onBeforeRender=function(T,S,A){this.matrixWorld.copyPosition(A.matrixWorld)},Object.defineProperty(l.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),n.update(l)),l.material.uniforms.envMap.value=x,l.material.uniforms.backgroundBlurriness.value=b.backgroundBlurriness,l.material.uniforms.backgroundIntensity.value=b.backgroundIntensity,l.material.uniforms.backgroundRotation.value.setFromMatrix4(q_.makeRotationFromEuler(b.backgroundRotation)).transpose(),x.isCubeTexture&&x.isRenderTargetTexture===!1&&l.material.uniforms.backgroundRotation.value.premultiply(Rp),l.material.toneMapped=it.getTransfer(x.colorSpace)!==_t,(h!==x||u!==x.version||d!==s.toneMapping)&&(l.material.needsUpdate=!0,h=x,u=x.version,d=s.toneMapping),l.layers.enableAll(),_.unshift(l,l.geometry,l.material,0,0,null)):x&&x.isTexture&&(c===void 0&&(c=new Ee(new Rt(2,2),new Bt({name:"BackgroundMaterial",uniforms:ks(Ei.background.uniforms),vertexShader:Ei.background.vertexShader,fragmentShader:Ei.background.fragmentShader,side:wi,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),c.geometry.deleteAttribute("normal"),Object.defineProperty(c.material,"map",{get:function(){return this.uniforms.t2D.value}}),n.update(c)),c.material.uniforms.t2D.value=x,c.material.uniforms.backgroundIntensity.value=b.backgroundIntensity,c.material.toneMapped=it.getTransfer(x.colorSpace)!==_t,x.matrixAutoUpdate===!0&&x.updateMatrix(),c.material.uniforms.uvTransform.value.copy(x.matrix),(h!==x||u!==x.version||d!==s.toneMapping)&&(c.material.needsUpdate=!0,h=x,u=x.version,d=s.toneMapping),c.layers.enableAll(),_.unshift(c,c.geometry,c.material,0,0,null))}function f(_,b){_.getRGB(hc,iu(s)),t.buffers.color.setClear(hc.r,hc.g,hc.b,b,r)}function m(){l!==void 0&&(l.geometry.dispose(),l.material.dispose(),l=void 0),c!==void 0&&(c.geometry.dispose(),c.material.dispose(),c=void 0)}return{getClearColor:function(){return a},setClearColor:function(_,b=1){a.set(_),o=b,f(a,o)},getClearAlpha:function(){return o},setClearAlpha:function(_){o=_,f(a,o)},render:g,addToRenderList:v,dispose:m}}function K_(s,e){let t=s.getParameter(s.MAX_VERTEX_ATTRIBS),n={},i=d(null),r=i,a=!1;function o(L,F,V,D,B){let X=!1,W=u(L,D,V,F);r!==W&&(r=W,l(r.object)),X=p(L,D,V,B),X&&g(L,D,V,B),B!==null&&e.update(B,s.ELEMENT_ARRAY_BUFFER),(X||a)&&(a=!1,x(L,F,V,D),B!==null&&s.bindBuffer(s.ELEMENT_ARRAY_BUFFER,e.get(B).buffer))}function c(){return s.createVertexArray()}function l(L){return s.bindVertexArray(L)}function h(L){return s.deleteVertexArray(L)}function u(L,F,V,D){let B=D.wireframe===!0,X=n[F.id];X===void 0&&(X={},n[F.id]=X);let W=L.isInstancedMesh===!0?L.id:0,re=X[W];re===void 0&&(re={},X[W]=re);let q=re[V.id];q===void 0&&(q={},re[V.id]=q);let j=q[B];return j===void 0&&(j=d(c()),q[B]=j),j}function d(L){let F=[],V=[],D=[];for(let B=0;B<t;B++)F[B]=0,V[B]=0,D[B]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:F,enabledAttributes:V,attributeDivisors:D,object:L,attributes:{},index:null}}function p(L,F,V,D){let B=r.attributes,X=F.attributes,W=0,re=V.getAttributes();for(let q in re)if(re[q].location>=0){let te=B[q],Ne=X[q];if(Ne===void 0&&(q==="instanceMatrix"&&L.instanceMatrix&&(Ne=L.instanceMatrix),q==="instanceColor"&&L.instanceColor&&(Ne=L.instanceColor)),te===void 0||te.attribute!==Ne||Ne&&te.data!==Ne.data)return!0;W++}return r.attributesNum!==W||r.index!==D}function g(L,F,V,D){let B={},X=F.attributes,W=0,re=V.getAttributes();for(let q in re)if(re[q].location>=0){let te=X[q];te===void 0&&(q==="instanceMatrix"&&L.instanceMatrix&&(te=L.instanceMatrix),q==="instanceColor"&&L.instanceColor&&(te=L.instanceColor));let Ne={};Ne.attribute=te,te&&te.data&&(Ne.data=te.data),B[q]=Ne,W++}r.attributes=B,r.attributesNum=W,r.index=D}function v(){let L=r.newAttributes;for(let F=0,V=L.length;F<V;F++)L[F]=0}function f(L){m(L,0)}function m(L,F){let V=r.newAttributes,D=r.enabledAttributes,B=r.attributeDivisors;V[L]=1,D[L]===0&&(s.enableVertexAttribArray(L),D[L]=1),B[L]!==F&&(s.vertexAttribDivisor(L,F),B[L]=F)}function _(){let L=r.newAttributes,F=r.enabledAttributes;for(let V=0,D=F.length;V<D;V++)F[V]!==L[V]&&(s.disableVertexAttribArray(V),F[V]=0)}function b(L,F,V,D,B,X,W){W===!0?s.vertexAttribIPointer(L,F,V,B,X):s.vertexAttribPointer(L,F,V,D,B,X)}function x(L,F,V,D){v();let B=D.attributes,X=V.getAttributes(),W=F.defaultAttributeValues;for(let re in X){let q=X[re];if(q.location>=0){let j=B[re];if(j===void 0&&(re==="instanceMatrix"&&L.instanceMatrix&&(j=L.instanceMatrix),re==="instanceColor"&&L.instanceColor&&(j=L.instanceColor)),j!==void 0){let te=j.normalized,Ne=j.itemSize,Ae=e.get(j);if(Ae===void 0)continue;let vt=Ae.buffer,ct=Ae.type,mt=Ae.bytesPerElement,Z=ct===s.INT||ct===s.UNSIGNED_INT||j.gpuType===Tl;if(j.isInterleavedBufferAttribute){let Q=j.data,_e=Q.stride,We=j.offset;if(Q.isInstancedInterleavedBuffer){for(let be=0;be<q.locationSize;be++)m(q.location+be,Q.meshPerAttribute);L.isInstancedMesh!==!0&&D._maxInstanceCount===void 0&&(D._maxInstanceCount=Q.meshPerAttribute*Q.count)}else for(let be=0;be<q.locationSize;be++)f(q.location+be);s.bindBuffer(s.ARRAY_BUFFER,vt);for(let be=0;be<q.locationSize;be++)b(q.location+be,Ne/q.locationSize,ct,te,_e*mt,(We+Ne/q.locationSize*be)*mt,Z)}else{if(j.isInstancedBufferAttribute){for(let Q=0;Q<q.locationSize;Q++)m(q.location+Q,j.meshPerAttribute);L.isInstancedMesh!==!0&&D._maxInstanceCount===void 0&&(D._maxInstanceCount=j.meshPerAttribute*j.count)}else for(let Q=0;Q<q.locationSize;Q++)f(q.location+Q);s.bindBuffer(s.ARRAY_BUFFER,vt);for(let Q=0;Q<q.locationSize;Q++)b(q.location+Q,Ne/q.locationSize,ct,te,Ne*mt,Ne/q.locationSize*Q*mt,Z)}}else if(W!==void 0){let te=W[re];if(te!==void 0)switch(te.length){case 2:s.vertexAttrib2fv(q.location,te);break;case 3:s.vertexAttrib3fv(q.location,te);break;case 4:s.vertexAttrib4fv(q.location,te);break;default:s.vertexAttrib1fv(q.location,te)}}}}_()}function T(){E();for(let L in n){let F=n[L];for(let V in F){let D=F[V];for(let B in D){let X=D[B];for(let W in X)h(X[W].object),delete X[W];delete D[B]}}delete n[L]}}function S(L){if(n[L.id]===void 0)return;let F=n[L.id];for(let V in F){let D=F[V];for(let B in D){let X=D[B];for(let W in X)h(X[W].object),delete X[W];delete D[B]}}delete n[L.id]}function A(L){for(let F in n){let V=n[F];for(let D in V){let B=V[D];if(B[L.id]===void 0)continue;let X=B[L.id];for(let W in X)h(X[W].object),delete X[W];delete B[L.id]}}}function y(L){for(let F in n){let V=n[F],D=L.isInstancedMesh===!0?L.id:0,B=V[D];if(B!==void 0){for(let X in B){let W=B[X];for(let re in W)h(W[re].object),delete W[re];delete B[X]}delete V[D],Object.keys(V).length===0&&delete n[F]}}}function E(){I(),a=!0,r!==i&&(r=i,l(r.object))}function I(){i.geometry=null,i.program=null,i.wireframe=!1}return{setup:o,reset:E,resetDefaultState:I,dispose:T,releaseStatesOfGeometry:S,releaseStatesOfObject:y,releaseStatesOfProgram:A,initAttributes:v,enableAttribute:f,disableUnusedAttributes:_}}function Z_(s,e,t){let n;function i(c){n=c}function r(c,l){s.drawArrays(n,c,l),t.update(l,n,1)}function a(c,l,h){h!==0&&(s.drawArraysInstanced(n,c,l,h),t.update(l,n,h))}function o(c,l,h){if(h===0)return;e.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n,c,0,l,0,h);let d=0;for(let p=0;p<h;p++)d+=l[p];t.update(d,n,1)}this.setMode=i,this.render=r,this.renderInstances=a,this.renderMultiDraw=o}function J_(s,e,t,n){let i;function r(){if(i!==void 0)return i;if(e.has("EXT_texture_filter_anisotropic")===!0){let A=e.get("EXT_texture_filter_anisotropic");i=s.getParameter(A.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else i=0;return i}function a(A){return!(A!==Un&&n.convert(A)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_FORMAT))}function o(A){let y=A===an&&(e.has("EXT_color_buffer_half_float")||e.has("EXT_color_buffer_float"));return!(A!==bn&&A!==Dn&&!y&&n.convert(A)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_TYPE))}function c(A){if(A==="highp"){if(s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.HIGH_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.HIGH_FLOAT).precision>0)return"highp";A="mediump"}return A==="mediump"&&s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.MEDIUM_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let l=t.precision!==void 0?t.precision:"highp",h=c(l);h!==l&&(Le("WebGLRenderer:",l,"not supported, using",h,"instead."),l=h);let u=t.logarithmicDepthBuffer===!0,d=t.reversedDepthBuffer===!0&&e.has("EXT_clip_control");t.reversedDepthBuffer===!0&&d===!1&&Le("WebGLRenderer: Unable to use reversed depth buffer due to missing EXT_clip_control extension. Fallback to default depth buffer.");let p=s.getParameter(s.MAX_TEXTURE_IMAGE_UNITS),g=s.getParameter(s.MAX_VERTEX_TEXTURE_IMAGE_UNITS),v=s.getParameter(s.MAX_TEXTURE_SIZE),f=s.getParameter(s.MAX_CUBE_MAP_TEXTURE_SIZE),m=s.getParameter(s.MAX_VERTEX_ATTRIBS),_=s.getParameter(s.MAX_VERTEX_UNIFORM_VECTORS),b=s.getParameter(s.MAX_VARYING_VECTORS),x=s.getParameter(s.MAX_FRAGMENT_UNIFORM_VECTORS),T=s.getParameter(s.MAX_SAMPLES),S=s.getParameter(s.SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:r,getMaxPrecision:c,textureFormatReadable:a,textureTypeReadable:o,precision:l,logarithmicDepthBuffer:u,reversedDepthBuffer:d,maxTextures:p,maxVertexTextures:g,maxTextureSize:v,maxCubemapSize:f,maxAttributes:m,maxVertexUniforms:_,maxVaryings:b,maxFragmentUniforms:x,maxSamples:T,samples:S}}function $_(s){let e=this,t=null,n=0,i=!1,r=!1,a=new ei,o=new Ze,c={value:null,needsUpdate:!1};this.uniform=c,this.numPlanes=0,this.numIntersection=0,this.init=function(u,d){let p=u.length!==0||d||n!==0||i;return i=d,n=u.length,p},this.beginShadows=function(){r=!0,h(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(u,d){t=h(u,d,0)},this.setState=function(u,d,p){let g=u.clippingPlanes,v=u.clipIntersection,f=u.clipShadows,m=s.get(u);if(!i||g===null||g.length===0||r&&!f)r?h(null):l();else{let _=r?0:n,b=_*4,x=m.clippingState||null;c.value=x,x=h(g,d,b,p);for(let T=0;T!==b;++T)x[T]=t[T];m.clippingState=x,this.numIntersection=v?this.numPlanes:0,this.numPlanes+=_}};function l(){c.value!==t&&(c.value=t,c.needsUpdate=n>0),e.numPlanes=n,e.numIntersection=0}function h(u,d,p,g){let v=u!==null?u.length:0,f=null;if(v!==0){if(f=c.value,g!==!0||f===null){let m=p+v*4,_=d.matrixWorldInverse;o.getNormalMatrix(_),(f===null||f.length<m)&&(f=new Float32Array(m));for(let b=0,x=p;b!==v;++b,x+=4)a.copy(u[b]).applyMatrix4(_,o),a.normal.toArray(f,x),f[x+3]=a.constant}c.value=f,c.needsUpdate=!0}return e.numPlanes=v,e.numIntersection=0,f}}var Or=4,j_=6,Q_=20,ey=256,$a=new Ti,op=new Me,ou=null,lu=0,cu=0,hu=!1,ty=new R,zs=new R,dc=class{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._sizeLods=[],this._lodMeshes=[],this._backgroundBox=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._blurMaterial=null,this._ggxMaterial=null}fromScene(e,t=0,n=.1,i=100,r={}){let{size:a=256,position:o=ty}=r;ou=this._renderer.getRenderTarget(),lu=this._renderer.getActiveCubeFace(),cu=this._renderer.getActiveMipmapLevel(),hu=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(a);let c=this._allocateTargets();return c.depthBuffer=!0,this._sceneToCubeUV(e,n,i,c,o),t>0&&this._blur(c,0,0,t),this._applyPMREM(c),this._cleanup(c),c}fromEquirectangular(e,t=null){return this._fromTexture(e,t)}fromCubemap(e,t=null){return this._fromTexture(e,t)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=hp(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=cp(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose(),this._backgroundBox!==null&&(this._backgroundBox.geometry.dispose(),this._backgroundBox.material.dispose())}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._ggxMaterial!==null&&this._ggxMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodMeshes.length;e++)this._lodMeshes[e].geometry.dispose()}_cleanup(e){this._renderer.setRenderTarget(ou,lu,cu),this._renderer.xr.enabled=hu,e.scissorTest=!1,Fr(e,0,0,e.width,e.height)}_fromTexture(e,t){e.mapping===us||e.mapping===Os?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),ou=this._renderer.getRenderTarget(),lu=this._renderer.getActiveCubeFace(),cu=this._renderer.getActiveMipmapLevel(),hu=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;let n=t||this._allocateTargets();return this._textureToCubeUV(e,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){let e=3*Math.max(this._cubeSize,112),t=4*this._cubeSize,n={magFilter:Xt,minFilter:Xt,generateMipmaps:!1,type:an,format:Un,colorSpace:gn,depthBuffer:!1},i=lp(e,t,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==t){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=lp(e,t,n);let{_lodMax:r}=this;({lodMeshes:this._lodMeshes,sizeLods:this._sizeLods}=ny(r)),this._blurMaterial=sy(r,e,t),this._ggxMaterial=iy(r,e,t)}return i}_compileMaterial(e){let t=new Ee(new tt,e);this._renderer.compile(t,$a)}_sceneToCubeUV(e,t,n,i,r){let c=new zt(90,1,t,n),l=[1,-1,1,1,1,1],h=[1,1,1,-1,-1,-1],u=this._renderer,d=u.autoClear,p=u.toneMapping;u.getClearColor(op),u.toneMapping=ri,u.autoClear=!1,u.state.buffers.depth.getReversed()&&(u.setRenderTarget(i),u.clearDepth(),u.setRenderTarget(null)),this._backgroundBox===null&&(this._backgroundBox=new Ee(new Mn,new Ye({name:"PMREM.Background",side:qt,depthWrite:!1,depthTest:!1})));let v=this._backgroundBox,f=v.material,m=!1,_=e.background;_?_.isColor&&(f.color.copy(_),e.background=null,m=!0):(f.color.copy(op),m=!0);for(let b=0;b<6;b++){let x=b%3;x===0?(c.up.set(0,l[b],0),c.position.set(r.x,r.y,r.z),c.lookAt(r.x+h[b],r.y,r.z)):x===1?(c.up.set(0,0,l[b]),c.position.set(r.x,r.y,r.z),c.lookAt(r.x,r.y+h[b],r.z)):(c.up.set(0,l[b],0),c.position.set(r.x,r.y,r.z),c.lookAt(r.x,r.y,r.z+h[b]));let T=this._cubeSize;Fr(i,x*T,b>2?T:0,T,T),u.setRenderTarget(i),m&&u.render(v,c),u.render(e,c)}u.toneMapping=p,u.autoClear=d,e.background=_}_textureToCubeUV(e,t){let n=this._renderer,i=e.mapping===us||e.mapping===Os;i?(this._cubemapMaterial===null&&(this._cubemapMaterial=hp()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=cp());let r=i?this._cubemapMaterial:this._equirectMaterial,a=this._lodMeshes[0];a.material=r;let o=r.uniforms;o.envMap.value=e;let c=this._cubeSize;Fr(t,0,0,3*c,2*c),n.setRenderTarget(t),n.render(a,$a)}_applyPMREM(e){let t=this._renderer,n=t.autoClear;t.autoClear=!1;let i=this._lodMeshes.length;for(let r=1;r<i;r++)this._applyGGXFilter(e,r-1,r);t.autoClear=n}_applyGGXFilter(e,t,n){let i=this._renderer,r=this._pingPongRenderTarget,a=this._ggxMaterial,o=this._lodMeshes[n];o.material=a;let c=a.uniforms,l=n/(this._lodMeshes.length-1),h=t/(this._lodMeshes.length-1),u=Math.sqrt(l*l-h*h),d=l*1.25,p=u*d,{_lodMax:g}=this,v=this._sizeLods[n],f=3*v*(n>g-Or?n-g+Or:0),m=4*(this._cubeSize-v);c.envMap.value=e.texture,c.roughness.value=p,c.mipInt.value=g-t,Fr(r,f,m,3*v,2*v),i.setRenderTarget(r),i.render(o,$a),c.envMap.value=r.texture,c.roughness.value=0,c.mipInt.value=g-n,Fr(e,f,m,3*v,2*v),i.setRenderTarget(e),i.render(o,$a)}_blur(e,t,n,i){let r=this._pingPongRenderTarget,a=Math.min(i,Math.PI)/Math.SQRT2;this._blurPass(e,r,t,n,a),this._blurPass(r,e,n,n,a)}_blurPass(e,t,n,i,r){let a=this._renderer,o=this._blurMaterial,c=this._lodMeshes[i];c.material=o;let l=o.uniforms;l.envMap.value=e.texture,l.sigma.value=r,l.mipInt.value=this._lodMax-n;let h=this._sizeLods[i],u=3*h*(i>this._lodMax-Or?i-this._lodMax+Or:0),d=4*(this._cubeSize-h);Fr(t,u,d,3*h,2*h),a.setRenderTarget(t),a.render(c,$a)}};function ny(s){let e=[],t=[],n=s,i=s-Or+1+j_;for(let r=0;r<i;r++){let a=Math.pow(2,n);e.push(a);let o=1/(a-2),c=-o,l=1+o,h=[c,c,l,c,l,l,c,c,l,l,c,l],u=6,d=6,p=3,g=new Float32Array(p*d*u),v=new Float32Array(p*d*u);for(let m=0;m<u;m++){let _=m%3*2/3-1,b=m>2?0:-1,x=[_,b,0,_+2/3,b,0,_+2/3,b+1,0,_,b,0,_+2/3,b+1,0,_,b+1,0];g.set(x,p*d*m);for(let T=0;T<d;T++){let S=h[T*2]*2-1,A=h[T*2+1]*2-1;m===0?zs.set(1,A,S):m===1?zs.set(-S,1,-A):m===2?zs.set(-S,A,1):m===3?zs.set(-1,A,-S):m===4?zs.set(-S,-1,A):zs.set(S,A,-1),zs.toArray(v,(m*d+T)*p)}}let f=new tt;f.setAttribute("position",new Ft(g,p)),f.setAttribute("outputDirection",new Ft(v,p)),t.push(new Ee(f,null)),n>Or&&n--}return{lodMeshes:t,sizeLods:e}}function lp(s,e,t){let n=new Jt(s,e,t);return n.texture.mapping=Ha,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function Fr(s,e,t,n,i){s.viewport.set(e,t,n,i),s.scissor.set(e,t,n,i)}function iy(s,e,t){return new Bt({name:"PMREMGGXConvolution",defines:{GGX_SAMPLES:ey,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/t,CUBEUV_MAX_MIP:`${s}.0`},uniforms:{envMap:{value:null},roughness:{value:0},mipInt:{value:0}},vertexShader:mc(),fragmentShader:`

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float roughness;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359

			// Van der Corput radical inverse
			float radicalInverse_VdC(uint bits) {
				bits = (bits << 16u) | (bits >> 16u);
				bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
				bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
				bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
				bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
				return float(bits) * 2.3283064365386963e-10; // / 0x100000000
			}

			// Hammersley sequence
			vec2 hammersley(uint i, uint N) {
				return vec2(float(i) / float(N), radicalInverse_VdC(i));
			}

			// GGX VNDF importance sampling (Eric Heitz 2018)
			// "Sampling the GGX Distribution of Visible Normals"
			// https://jcgt.org/published/0007/04/01/
			vec3 importanceSampleGGX_VNDF(vec2 Xi, vec3 V, float roughness) {
				float alpha = roughness * roughness;

				// Section 4.1: Orthonormal basis
				vec3 T1 = vec3(1.0, 0.0, 0.0);
				vec3 T2 = cross(V, T1);

				// Section 4.2: Parameterization of projected area
				float r = sqrt(Xi.x);
				float phi = 2.0 * PI * Xi.y;
				float t1 = r * cos(phi);
				float t2 = r * sin(phi);
				float s = 0.5 * (1.0 + V.z);
				t2 = (1.0 - s) * sqrt(1.0 - t1 * t1) + s * t2;

				// Section 4.3: Reprojection onto hemisphere
				vec3 Nh = t1 * T1 + t2 * T2 + sqrt(max(0.0, 1.0 - t1 * t1 - t2 * t2)) * V;

				// Section 3.4: Transform back to ellipsoid configuration
				return normalize(vec3(alpha * Nh.x, alpha * Nh.y, max(0.0, Nh.z)));
			}

			void main() {
				vec3 N = normalize(vOutputDirection);
				vec3 V = N; // Assume view direction equals normal for pre-filtering

				vec3 prefilteredColor = vec3(0.0);
				float totalWeight = 0.0;

				// For very low roughness, just sample the environment directly
				if (roughness < 0.001) {
					gl_FragColor = vec4(bilinearCubeUV(envMap, N, mipInt), 1.0);
					return;
				}

				// Tangent space basis for VNDF sampling
				vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
				vec3 tangent = normalize(cross(up, N));
				vec3 bitangent = cross(N, tangent);

				for(uint i = 0u; i < uint(GGX_SAMPLES); i++) {
					vec2 Xi = hammersley(i, uint(GGX_SAMPLES));

					// For PMREM, V = N, so in tangent space V is always (0, 0, 1)
					vec3 H_tangent = importanceSampleGGX_VNDF(Xi, vec3(0.0, 0.0, 1.0), roughness);

					// Transform H back to world space
					vec3 H = normalize(tangent * H_tangent.x + bitangent * H_tangent.y + N * H_tangent.z);
					vec3 L = normalize(2.0 * dot(V, H) * H - V);

					float NdotL = max(dot(N, L), 0.0);

					if(NdotL > 0.0) {
						// Sample environment at fixed mip level
						// VNDF importance sampling handles the distribution filtering
						vec3 sampleColor = bilinearCubeUV(envMap, L, mipInt);

						// Weight by NdotL for the split-sum approximation
						// VNDF PDF naturally accounts for the visible microfacet distribution
						prefilteredColor += sampleColor * NdotL;
						totalWeight += NdotL;
					}
				}

				if (totalWeight > 0.0) {
					prefilteredColor = prefilteredColor / totalWeight;
				}

				gl_FragColor = vec4(prefilteredColor, 1.0);
			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function sy(s,e,t){return new Bt({name:"SphericalGaussianBlur",defines:{SAMPLES:Q_,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/t,CUBEUV_MAX_MIP:`${s}.0`},uniforms:{envMap:{value:null},sigma:{value:0},mipInt:{value:0}},vertexShader:mc(),fragmentShader:`

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float sigma;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359
			#define GOLDEN_ANGLE 2.39996322973

			void main() {

				if ( sigma == 0.0 ) {

					gl_FragColor = vec4( bilinearCubeUV( envMap, vOutputDirection, mipInt ), 1.0 );
					return;

				}

				vec3 outputDirection = normalize( vOutputDirection );

				vec3 up = abs( outputDirection.z ) < 0.999 ? vec3( 0.0, 0.0, 1.0 ) : vec3( 1.0, 0.0, 0.0 );
				vec3 tangent = normalize( cross( up, outputDirection ) );
				vec3 bitangent = cross( outputDirection, tangent );

				// Truncate the kernel at three standard deviations or at the antipode.
				float thetaMax = min( 3.0 * sigma, PI );
				float truncation = 1.0 - exp( - 0.5 * thetaMax * thetaMax / ( sigma * sigma ) );

				vec3 accumColor = vec3( 0.0 );
				float accumWeight = 0.0;

				for ( int i = 0; i < SAMPLES; i ++ ) {

					// Stratified inverse-CDF sampling of the Gaussian, placed on a golden-angle spiral.
					float stratum = ( float( i ) + 0.5 ) / float( SAMPLES );
					float theta = sigma * sqrt( - 2.0 * log( 1.0 - stratum * truncation ) );
					float phi = float( i ) * GOLDEN_ANGLE;

					vec3 offset = cos( phi ) * tangent + sin( phi ) * bitangent;
					vec3 sampleDirection = cos( theta ) * outputDirection + sin( theta ) * offset;

					// Correct the planar sample density to solid angle.
					float weight = sin( theta ) / theta;

					accumColor += weight * bilinearCubeUV( envMap, sampleDirection, mipInt );
					accumWeight += weight;

				}

				gl_FragColor = vec4( accumColor / accumWeight, 1.0 );

			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function cp(){return new Bt({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:mc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function hp(){return new Bt({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:mc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function mc(){return`

		precision mediump float;
		precision mediump int;

		attribute vec3 outputDirection;

		varying vec3 vOutputDirection;

		void main() {

			vOutputDirection = outputDirection;
			gl_Position = vec4( position, 1.0 );

		}
	`}var fc=class extends Jt{constructor(e=1,t={}){super(e,e,t),this.isWebGLCubeRenderTarget=!0;let n={width:e,height:e,depth:1},i=[n,n,n,n,n,n];this.texture=new ga(i),this._setTextureOptions(t),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(e,t){this.texture.type=t.type,this.texture.colorSpace=t.colorSpace,this.texture.generateMipmaps=t.generateMipmaps,this.texture.minFilter=t.minFilter,this.texture.magFilter=t.magFilter;let n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},i=new Mn(5,5,5),r=new Bt({name:"CubemapFromEquirect",uniforms:ks(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:qt,blending:Xn});r.uniforms.tEquirect.value=t;let a=new Ee(i,r),o=t.minFilter;return t.minFilter===ai&&(t.minFilter=Xt),new vl(1,10,this).update(e,a),t.minFilter=o,a.geometry.dispose(),a.material.dispose(),this}clear(e,t=!0,n=!0,i=!0){let r=e.getRenderTarget();for(let a=0;a<6;a++)e.setRenderTarget(this,a),e.clear(t,n,i);e.setRenderTarget(r)}};function ry(s){let e=new WeakMap,t=new WeakMap,n=null;function i(d,p=!1){return d==null?null:p?a(d):r(d)}function r(d){if(d&&d.isTexture){let p=d.mapping;if(p===Pr||p===Sl)if(e.has(d)){let g=e.get(d).texture;return o(g,d.mapping)}else{let g=d.image;if(g&&g.height>0){let v=new fc(g.height);return v.fromEquirectangularTexture(s,d),e.set(d,v),d.addEventListener("dispose",l),o(v.texture,d.mapping)}else return null}}return d}function a(d){if(d&&d.isTexture){let p=d.mapping,g=p===Pr||p===Sl,v=p===us||p===Os;if(g||v){let f=t.get(d),m=f!==void 0?f.texture.pmremVersion:0;if(d.isRenderTargetTexture&&d.pmremVersion!==m)return n===null&&(n=new dc(s)),f=g?n.fromEquirectangular(d,f):n.fromCubemap(d,f),f.texture.pmremVersion=d.pmremVersion,t.set(d,f),f.texture;if(f!==void 0)return f.texture;{let _=d.image;return g&&_&&_.height>0||v&&_&&c(_)?(n===null&&(n=new dc(s)),f=g?n.fromEquirectangular(d):n.fromCubemap(d),f.texture.pmremVersion=d.pmremVersion,t.set(d,f),d.addEventListener("dispose",h),f.texture):null}}}return d}function o(d,p){return p===Pr?d.mapping=us:p===Sl&&(d.mapping=Os),d}function c(d){let p=0,g=6;for(let v=0;v<g;v++)d[v]!==void 0&&p++;return p===g}function l(d){let p=d.target;p.removeEventListener("dispose",l);let g=e.get(p);g!==void 0&&(e.delete(p),g.dispose())}function h(d){let p=d.target;p.removeEventListener("dispose",h);let g=t.get(p);g!==void 0&&(t.delete(p),g.dispose())}function u(){e=new WeakMap,t=new WeakMap,n!==null&&(n.dispose(),n=null)}return{get:i,dispose:u}}function ay(s){let e={};function t(n){if(e[n]!==void 0)return e[n];let i=s.getExtension(n);return e[n]=i,i}return{has:function(n){return t(n)!==null},init:function(){t("EXT_color_buffer_float"),t("WEBGL_clip_cull_distance"),t("OES_texture_float_linear"),t("EXT_color_buffer_half_float"),t("WEBGL_multisampled_render_to_texture"),t("WEBGL_render_shared_exponent")},get:function(n){let i=t(n);return i===null&&bs("WebGLRenderer: "+n+" extension not supported."),i}}}function oy(s,e,t,n){let i={},r=new WeakMap;function a(u){let d=u.target;d.index!==null&&e.remove(d.index);for(let g in d.attributes)e.remove(d.attributes[g]);d.removeEventListener("dispose",a),delete i[d.id];let p=r.get(d);p&&(e.remove(p),r.delete(d)),n.releaseStatesOfGeometry(d),d.isInstancedBufferGeometry===!0&&delete d._maxInstanceCount,t.memory.geometries--}function o(u,d){return i[d.id]===!0||(d.addEventListener("dispose",a),i[d.id]=!0,t.memory.geometries++),d}function c(u){let d=u.attributes;for(let p in d)e.update(d[p],s.ARRAY_BUFFER)}function l(u){let d=[],p=u.index,g=u.attributes.position,v=0;if(g===void 0)return;if(p!==null){let _=p.array;v=p.version;for(let b=0,x=_.length;b<x;b+=3){let T=_[b+0],S=_[b+1],A=_[b+2];d.push(T,S,S,A,A,T)}}else{let _=g.array;v=g.version;for(let b=0,x=_.length/3-1;b<x;b+=3){let T=b+0,S=b+1,A=b+2;d.push(T,S,S,A,A,T)}}let f=new(g.count>=65535?da:Es)(d,1);f.version=v;let m=r.get(u);m&&e.remove(m),r.set(u,f)}function h(u){let d=r.get(u);if(d){let p=u.index;p!==null&&d.version<p.version&&l(u)}else l(u);return r.get(u)}return{get:o,update:c,getWireframeAttribute:h}}function ly(s,e,t){let n;function i(u){n=u}let r,a;function o(u){r=u.type,a=u.bytesPerElement}function c(u,d){s.drawElements(n,d,r,u*a),t.update(d,n,1)}function l(u,d,p){p!==0&&(s.drawElementsInstanced(n,d,r,u*a,p),t.update(d,n,p))}function h(u,d,p){if(p===0)return;e.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n,d,0,r,u,0,p);let v=0;for(let f=0;f<p;f++)v+=d[f];t.update(v,n,1)}this.setMode=i,this.setIndex=o,this.render=c,this.renderInstances=l,this.renderMultiDraw=h}function cy(s){let e={geometries:0,textures:0},t={frame:0,calls:0,triangles:0,points:0,lines:0};function n(r,a,o){switch(t.calls++,a){case s.TRIANGLES:t.triangles+=o*(r/3);break;case s.LINES:t.lines+=o*(r/2);break;case s.LINE_STRIP:t.lines+=o*(r-1);break;case s.LINE_LOOP:t.lines+=o*r;break;case s.POINTS:t.points+=o*r;break;default:He("WebGLInfo: Unknown draw mode:",a);break}}function i(){t.calls=0,t.triangles=0,t.points=0,t.lines=0}return{memory:e,render:t,programs:null,autoReset:!0,reset:i,update:n}}function hy(s,e,t){let n=new WeakMap,i=new At;function r(a,o,c){let l=a.morphTargetInfluences,h=o.morphAttributes.position||o.morphAttributes.normal||o.morphAttributes.color,u=h!==void 0?h.length:0,d=n.get(o);if(d===void 0||d.count!==u){let E=function(){A.dispose(),n.delete(o),o.removeEventListener("dispose",E)};d!==void 0&&d.texture.dispose();let p=o.morphAttributes.position!==void 0,g=o.morphAttributes.normal!==void 0,v=o.morphAttributes.color!==void 0,f=o.morphAttributes.position||[],m=o.morphAttributes.normal||[],_=o.morphAttributes.color||[],b=0;p===!0&&(b=1),g===!0&&(b=2),v===!0&&(b=3);let x=o.attributes.position.count*b,T=1;x>e.maxTextureSize&&(T=Math.ceil(x/e.maxTextureSize),x=e.maxTextureSize);let S=new Float32Array(x*T*4*u),A=new la(S,x,T,u);A.type=Dn,A.needsUpdate=!0;let y=b*4;for(let I=0;I<u;I++){let L=f[I],F=m[I],V=_[I],D=x*T*4*I;for(let B=0;B<L.count;B++){let X=B*y;p===!0&&(i.fromBufferAttribute(L,B),S[D+X+0]=i.x,S[D+X+1]=i.y,S[D+X+2]=i.z,S[D+X+3]=0),g===!0&&(i.fromBufferAttribute(F,B),S[D+X+4]=i.x,S[D+X+5]=i.y,S[D+X+6]=i.z,S[D+X+7]=0),v===!0&&(i.fromBufferAttribute(V,B),S[D+X+8]=i.x,S[D+X+9]=i.y,S[D+X+10]=i.z,S[D+X+11]=V.itemSize===4?i.w:1)}}d={count:u,texture:A,size:new ne(x,T)},n.set(o,d),o.addEventListener("dispose",E)}if(a.isInstancedMesh===!0&&a.morphTexture!==null)c.getUniforms().setValue(s,"morphTexture",a.morphTexture,t);else{let p=0;for(let v=0;v<l.length;v++)p+=l[v];let g=o.morphTargetsRelative?1:1-p;c.getUniforms().setValue(s,"morphTargetBaseInfluence",g),c.getUniforms().setValue(s,"morphTargetInfluences",l)}c.getUniforms().setValue(s,"morphTargetsTexture",d.texture,t),c.getUniforms().setValue(s,"morphTargetsTextureSize",d.size)}return{update:r}}function uy(s,e,t,n,i){let r=new WeakMap;function a(l){let h=i.render.frame,u=l.geometry,d=e.get(l,u);if(r.get(d)!==h&&(e.update(d),r.set(d,h)),l.isInstancedMesh&&(l.hasEventListener("dispose",c)===!1&&l.addEventListener("dispose",c),r.get(l)!==h&&(t.update(l.instanceMatrix,s.ARRAY_BUFFER),l.instanceColor!==null&&t.update(l.instanceColor,s.ARRAY_BUFFER),r.set(l,h))),l.isSkinnedMesh){let p=l.skeleton;r.get(p)!==h&&(p.update(),r.set(p,h))}return d}function o(){r=new WeakMap}function c(l){let h=l.target;h.removeEventListener("dispose",c),n.releaseStatesOfObject(h),t.remove(h.instanceMatrix),h.instanceColor!==null&&t.remove(h.instanceColor)}return{update:a,dispose:o}}var dy={[Oa]:"LINEAR_TONE_MAPPING",[Ba]:"REINHARD_TONE_MAPPING",[ka]:"CINEON_TONE_MAPPING",[Fs]:"ACES_FILMIC_TONE_MAPPING",[Ga]:"AGX_TONE_MAPPING",[Va]:"NEUTRAL_TONE_MAPPING",[za]:"CUSTOM_TONE_MAPPING"};function fy(s,e,t,n,i,r){let a=new Jt(e,t,{type:s,depthBuffer:i,stencilBuffer:r,samples:n?4:0,storeMultisampledDepthBuffer:!1,storeMultisampledStencilBuffer:!1,resolveDepthBuffer:!1,resolveStencilBuffer:!1}),o=null,c=null,l=new tt;l.setAttribute("position",new Oe([-1,3,0,-1,-1,0,3,-1,0],3)),l.setAttribute("uv",new Oe([0,2,0,0,2,0],2));let h=new Ar({uniforms:{tDiffuse:{value:null}},vertexShader:`
			precision highp float;

			uniform mat4 modelViewMatrix;
			uniform mat4 projectionMatrix;

			attribute vec3 position;
			attribute vec2 uv;

			varying vec2 vUv;

			void main() {
				vUv = uv;
				gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
			}`,fragmentShader:`
			precision highp float;

			uniform sampler2D tDiffuse;

			varying vec2 vUv;

			#include <tonemapping_pars_fragment>
			#include <colorspace_pars_fragment>

			void main() {
				gl_FragColor = texture2D( tDiffuse, vUv );

				#ifdef LINEAR_TONE_MAPPING
					gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );
				#elif defined( REINHARD_TONE_MAPPING )
					gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );
				#elif defined( CINEON_TONE_MAPPING )
					gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );
				#elif defined( ACES_FILMIC_TONE_MAPPING )
					gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );
				#elif defined( AGX_TONE_MAPPING )
					gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );
				#elif defined( NEUTRAL_TONE_MAPPING )
					gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );
				#elif defined( CUSTOM_TONE_MAPPING )
					gl_FragColor.rgb = CustomToneMapping( gl_FragColor.rgb );
				#endif

				#ifdef SRGB_TRANSFER
					gl_FragColor = sRGBTransferOETF( gl_FragColor );
				#endif
			}`,depthTest:!1,depthWrite:!1}),u=new Ee(l,h),d=new Ti(-1,1,1,-1,0,1),p=null,g=null,v=!1,f,m=null,_=[],b=!1;this.setSize=function(x,T){a.setSize(x,T),o!==null&&o.setSize(x,T),c!==null&&c.setSize(x,T);for(let S=0;S<_.length;S++){let A=_[S];A.setSize&&A.setSize(x,T)}},this.setEffects=function(x){_=x,b=_.length>0&&_[0].isRenderPass===!0;let T=a.width,S=a.height;_.length>0&&o===null&&(o=new Jt(T,S,{type:an,depthBuffer:!1,stencilBuffer:!1}),c=new Jt(T,S,{type:an,depthBuffer:!1,stencilBuffer:!1}));for(let A=0;A<_.length;A++){let y=_[A];y.setSize&&y.setSize(T,S)}},this.begin=function(x,T){if(v||x.toneMapping===ri&&_.length===0)return!1;if(m=T,T!==null){let S=T.width,A=T.height;(a.width!==S||a.height!==A)&&this.setSize(S,A)}return b===!1&&x.setRenderTarget(a),f=x.toneMapping,x.toneMapping=ri,!0},this.hasRenderPass=function(){return b},this.end=function(x,T){x.toneMapping=f,v=!0;let S=a,A=o;for(let y=0;y<_.length;y++){let E=_[y];E.enabled!==!1&&(E.render(x,A,S,T),E.needsSwap!==!1&&(S=A,A=A===o?c:o))}if(p!==x.outputColorSpace||g!==x.toneMapping){p=x.outputColorSpace,g=x.toneMapping,h.defines={},it.getTransfer(p)===_t&&(h.defines.SRGB_TRANSFER="");let y=dy[g];y&&(h.defines[y]=""),h.needsUpdate=!0}h.uniforms.tDiffuse.value=S.texture,x.setRenderTarget(m),x.render(u,d),m=null,v=!1},this.isCompositing=function(){return v},this.dispose=function(){a.dispose(),o!==null&&o.dispose(),c!==null&&c.dispose(),l.dispose(),h.dispose()}}var Ip=new jt,fu=new as(1,1),Pp=new la,Lp=new nl,Np=new ga,up=[],dp=[],fp=new Float32Array(16),pp=new Float32Array(9),mp=new Float32Array(4);function kr(s,e,t){let n=s[0];if(n<=0||n>0)return s;let i=e*t,r=up[i];if(r===void 0&&(r=new Float32Array(i),up[i]=r),e!==0){n.toArray(r,0);for(let a=1,o=0;a!==e;++a)o+=t,s[a].toArray(r,o)}return r}function Qt(s,e){if(s.length!==e.length)return!1;for(let t=0,n=s.length;t<n;t++)if(s[t]!==e[t])return!1;return!0}function en(s,e){for(let t=0,n=e.length;t<n;t++)s[t]=e[t]}function gc(s,e){let t=dp[e];t===void 0&&(t=new Int32Array(e),dp[e]=t);for(let n=0;n!==e;++n)t[n]=s.allocateTextureUnit();return t}function py(s,e){let t=this.cache;t[0]!==e&&(s.uniform1f(this.addr,e),t[0]=e)}function my(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(s.uniform2f(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Qt(t,e))return;s.uniform2fv(this.addr,e),en(t,e)}}function gy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(s.uniform3f(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else if(e.r!==void 0)(t[0]!==e.r||t[1]!==e.g||t[2]!==e.b)&&(s.uniform3f(this.addr,e.r,e.g,e.b),t[0]=e.r,t[1]=e.g,t[2]=e.b);else{if(Qt(t,e))return;s.uniform3fv(this.addr,e),en(t,e)}}function xy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(s.uniform4f(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Qt(t,e))return;s.uniform4fv(this.addr,e),en(t,e)}}function _y(s,e){let t=this.cache,n=e.elements;if(n===void 0){if(Qt(t,e))return;s.uniformMatrix2fv(this.addr,!1,e),en(t,e)}else{if(Qt(t,n))return;mp.set(n),s.uniformMatrix2fv(this.addr,!1,mp),en(t,n)}}function yy(s,e){let t=this.cache,n=e.elements;if(n===void 0){if(Qt(t,e))return;s.uniformMatrix3fv(this.addr,!1,e),en(t,e)}else{if(Qt(t,n))return;pp.set(n),s.uniformMatrix3fv(this.addr,!1,pp),en(t,n)}}function vy(s,e){let t=this.cache,n=e.elements;if(n===void 0){if(Qt(t,e))return;s.uniformMatrix4fv(this.addr,!1,e),en(t,e)}else{if(Qt(t,n))return;fp.set(n),s.uniformMatrix4fv(this.addr,!1,fp),en(t,n)}}function My(s,e){let t=this.cache;t[0]!==e&&(s.uniform1i(this.addr,e),t[0]=e)}function Sy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(s.uniform2i(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Qt(t,e))return;s.uniform2iv(this.addr,e),en(t,e)}}function by(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(s.uniform3i(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Qt(t,e))return;s.uniform3iv(this.addr,e),en(t,e)}}function Ty(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(s.uniform4i(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Qt(t,e))return;s.uniform4iv(this.addr,e),en(t,e)}}function wy(s,e){let t=this.cache;t[0]!==e&&(s.uniform1ui(this.addr,e),t[0]=e)}function Ay(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(s.uniform2ui(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Qt(t,e))return;s.uniform2uiv(this.addr,e),en(t,e)}}function Ey(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(s.uniform3ui(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Qt(t,e))return;s.uniform3uiv(this.addr,e),en(t,e)}}function Cy(s,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(s.uniform4ui(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Qt(t,e))return;s.uniform4uiv(this.addr,e),en(t,e)}}function Ry(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i);let r;this.type===s.SAMPLER_2D_SHADOW?(fu.compareFunction=t.isReversedDepthBuffer()?cc:lc,r=fu):r=Ip,t.setTexture2D(e||r,i)}function Iy(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),t.setTexture3D(e||Lp,i)}function Py(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),t.setTextureCube(e||Np,i)}function Ly(s,e,t){let n=this.cache,i=t.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),t.setTexture2DArray(e||Pp,i)}function Ny(s){switch(s){case 5126:return py;case 35664:return my;case 35665:return gy;case 35666:return xy;case 35674:return _y;case 35675:return yy;case 35676:return vy;case 5124:case 35670:return My;case 35667:case 35671:return Sy;case 35668:case 35672:return by;case 35669:case 35673:return Ty;case 5125:return wy;case 36294:return Ay;case 36295:return Ey;case 36296:return Cy;case 35678:case 36198:case 36298:case 36306:case 35682:return Ry;case 35679:case 36299:case 36307:return Iy;case 35680:case 36300:case 36308:case 36293:return Py;case 36289:case 36303:case 36311:case 36292:return Ly}}function Dy(s,e){s.uniform1fv(this.addr,e)}function Uy(s,e){let t=kr(e,this.size,2);s.uniform2fv(this.addr,t)}function Fy(s,e){let t=kr(e,this.size,3);s.uniform3fv(this.addr,t)}function Oy(s,e){let t=kr(e,this.size,4);s.uniform4fv(this.addr,t)}function By(s,e){let t=kr(e,this.size,4);s.uniformMatrix2fv(this.addr,!1,t)}function ky(s,e){let t=kr(e,this.size,9);s.uniformMatrix3fv(this.addr,!1,t)}function zy(s,e){let t=kr(e,this.size,16);s.uniformMatrix4fv(this.addr,!1,t)}function Gy(s,e){s.uniform1iv(this.addr,e)}function Vy(s,e){s.uniform2iv(this.addr,e)}function Hy(s,e){s.uniform3iv(this.addr,e)}function Wy(s,e){s.uniform4iv(this.addr,e)}function Xy(s,e){s.uniform1uiv(this.addr,e)}function qy(s,e){s.uniform2uiv(this.addr,e)}function Yy(s,e){s.uniform3uiv(this.addr,e)}function Ky(s,e){s.uniform4uiv(this.addr,e)}function Zy(s,e,t){let n=this.cache,i=e.length,r=gc(t,i);Qt(n,r)||(s.uniform1iv(this.addr,r),en(n,r));let a;this.type===s.SAMPLER_2D_SHADOW?a=fu:a=Ip;for(let o=0;o!==i;++o)t.setTexture2D(e[o]||a,r[o])}function Jy(s,e,t){let n=this.cache,i=e.length,r=gc(t,i);Qt(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let a=0;a!==i;++a)t.setTexture3D(e[a]||Lp,r[a])}function $y(s,e,t){let n=this.cache,i=e.length,r=gc(t,i);Qt(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let a=0;a!==i;++a)t.setTextureCube(e[a]||Np,r[a])}function jy(s,e,t){let n=this.cache,i=e.length,r=gc(t,i);Qt(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let a=0;a!==i;++a)t.setTexture2DArray(e[a]||Pp,r[a])}function Qy(s){switch(s){case 5126:return Dy;case 35664:return Uy;case 35665:return Fy;case 35666:return Oy;case 35674:return By;case 35675:return ky;case 35676:return zy;case 5124:case 35670:return Gy;case 35667:case 35671:return Vy;case 35668:case 35672:return Hy;case 35669:case 35673:return Wy;case 5125:return Xy;case 36294:return qy;case 36295:return Yy;case 36296:return Ky;case 35678:case 36198:case 36298:case 36306:case 35682:return Zy;case 35679:case 36299:case 36307:return Jy;case 35680:case 36300:case 36308:case 36293:return $y;case 36289:case 36303:case 36311:case 36292:return jy}}var pu=class{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.setValue=Ny(t.type)}},mu=class{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.size=t.size,this.setValue=Qy(t.type)}},gu=class{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,t,n){let i=this.seq;for(let r=0,a=i.length;r!==a;++r){let o=i[r];o.setValue(e,t[o.id],n)}}},uu=/(\w+)(\])?(\[|\.)?/g;function gp(s,e){s.seq.push(e),s.map[e.id]=e}function ev(s,e,t){let n=s.name,i=n.length;for(uu.lastIndex=0;;){let r=uu.exec(n),a=uu.lastIndex,o=r[1],c=r[2]==="]",l=r[3];if(c&&(o=o|0),l===void 0||l==="["&&a+2===i){gp(t,l===void 0?new pu(o,s,e):new mu(o,s,e));break}else{let u=t.map[o];u===void 0&&(u=new gu(o),gp(t,u)),t=u}}}var Br=class{constructor(e,t){this.seq=[],this.map={};let n=e.getProgramParameter(t,e.ACTIVE_UNIFORMS);for(let a=0;a<n;++a){let o=e.getActiveUniform(t,a),c=e.getUniformLocation(t,o.name);ev(o,c,this)}let i=[],r=[];for(let a of this.seq)a.type===e.SAMPLER_2D_SHADOW||a.type===e.SAMPLER_CUBE_SHADOW||a.type===e.SAMPLER_2D_ARRAY_SHADOW?i.push(a):r.push(a);i.length>0&&(this.seq=i.concat(r))}setValue(e,t,n,i){let r=this.map[t];r!==void 0&&r.setValue(e,n,i)}setOptional(e,t,n){let i=t[n];i!==void 0&&this.setValue(e,n,i)}static upload(e,t,n,i){for(let r=0,a=t.length;r!==a;++r){let o=t[r],c=n[o.id];c.needsUpdate!==!1&&o.setValue(e,c.value,i)}}static seqWithValue(e,t){let n=[];for(let i=0,r=e.length;i!==r;++i){let a=e[i];a.id in t&&n.push(a)}return n}};function xp(s,e,t){let n=s.createShader(e);return s.shaderSource(n,t),s.compileShader(n),n}var tv=37297,nv=0;function iv(s,e){let t=s.split(`
`),n=[],i=Math.max(e-6,0),r=Math.min(e+6,t.length);for(let a=i;a<r;a++){let o=a+1;n.push(`${o===e?">":" "} ${o}: ${t[a]}`)}return n.join(`
`)}var _p=new Ze;function sv(s){it._getMatrix(_p,it.workingColorSpace,s);let e=`mat3( ${_p.elements.map(t=>t.toFixed(4))} )`;switch(it.getTransfer(s)){case aa:return[e,"LinearTransferOETF"];case _t:return[e,"sRGBTransferOETF"];default:return Le("WebGLProgram: Unsupported color space: ",s),[e,"LinearTransferOETF"]}}function yp(s,e,t){let n=s.getShaderParameter(e,s.COMPILE_STATUS),r=(s.getShaderInfoLog(e)||"").trim();if(n&&r==="")return"";let a=/ERROR: 0:(\d+)/.exec(r);if(a){let o=parseInt(a[1]);return t.toUpperCase()+`

`+r+`

`+iv(s.getShaderSource(e),o)}else return r}function rv(s,e){let t=sv(e);return[`vec4 ${s}( vec4 value ) {`,`	return ${t[1]}( vec4( value.rgb * ${t[0]}, value.a ) );`,"}"].join(`
`)}var av={[Oa]:"Linear",[Ba]:"Reinhard",[ka]:"Cineon",[Fs]:"ACESFilmic",[Ga]:"AgX",[Va]:"Neutral",[za]:"Custom"};function ov(s,e){let t=av[e];return t===void 0?(Le("WebGLProgram: Unsupported toneMapping:",e),"vec3 "+s+"( vec3 color ) { return LinearToneMapping( color ); }"):"vec3 "+s+"( vec3 color ) { return "+t+"ToneMapping( color ); }"}var uc=new R;function lv(){it.getLuminanceCoefficients(uc);let s=uc.x.toFixed(4),e=uc.y.toFixed(4),t=uc.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${s}, ${e}, ${t} );`,"	return dot( weights, rgb );","}"].join(`
`)}function cv(s){return[s.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",s.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(Qa).join(`
`)}function hv(s){let e=[];for(let t in s){let n=s[t];n!==!1&&e.push("#define "+t+" "+n)}return e.join(`
`)}function uv(s,e){let t={},n=s.getProgramParameter(e,s.ACTIVE_ATTRIBUTES);for(let i=0;i<n;i++){let r=s.getActiveAttrib(e,i),a=r.name,o=1;r.type===s.FLOAT_MAT2&&(o=2),r.type===s.FLOAT_MAT3&&(o=3),r.type===s.FLOAT_MAT4&&(o=4),t[a]={type:r.type,location:s.getAttribLocation(e,a),locationSize:o}}return t}function Qa(s){return s!==""}function vp(s,e){let t=e.numSpotLightShadows+e.numSpotLightMaps-e.numSpotLightShadowsWithMaps;return s.replace(/NUM_SUN_LIGHTS/g,e.numSunLights).replace(/NUM_DIR_LIGHTS/g,e.numDirLights).replace(/NUM_SPOT_LIGHTS/g,e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,t).replace(/NUM_RECT_AREA_LIGHTS/g,e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,e.numPointLights).replace(/NUM_HEMI_LIGHTS/g,e.numHemiLights).replace(/NUM_SUN_LIGHT_SHADOWS/g,e.numSunLightShadows).replace(/NUM_DIR_LIGHT_SHADOWS/g,e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,e.numPointLightShadows)}function Mp(s,e){return s.replace(/NUM_CLIPPING_PLANES/g,e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,e.numClippingPlanes-e.numClipIntersection)}var dv=/^[ \t]*#include +<([\w\d./]+)>/gm;function xu(s){return s.replace(dv,pv)}var fv=new Map;function pv(s,e){let t=at[e];if(t===void 0){let n=fv.get(e);if(n!==void 0)t=at[n],Le('WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',e,n);else throw new Error("THREE.WebGLProgram: Can not resolve #include <"+e+">")}return xu(t)}var mv=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function Sp(s){return s.replace(mv,gv)}function gv(s,e,t,n){let i="";for(let r=parseInt(e);r<parseInt(t);r++)i+=n.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return i}function bp(s){let e=`precision ${s.precision} float;
	precision ${s.precision} int;
	precision ${s.precision} sampler2D;
	precision ${s.precision} samplerCube;
	precision ${s.precision} sampler3D;
	precision ${s.precision} sampler2DArray;
	precision ${s.precision} sampler2DShadow;
	precision ${s.precision} samplerCubeShadow;
	precision ${s.precision} sampler2DArrayShadow;
	precision ${s.precision} isampler2D;
	precision ${s.precision} isampler3D;
	precision ${s.precision} isamplerCube;
	precision ${s.precision} isampler2DArray;
	precision ${s.precision} usampler2D;
	precision ${s.precision} usampler3D;
	precision ${s.precision} usamplerCube;
	precision ${s.precision} usampler2DArray;
	`;return s.precision==="highp"?e+=`
#define HIGH_PRECISION`:s.precision==="mediump"?e+=`
#define MEDIUM_PRECISION`:s.precision==="lowp"&&(e+=`
#define LOW_PRECISION`),e}var xv={[Ds]:"SHADOWMAP_TYPE_PCF",[Rr]:"SHADOWMAP_TYPE_VSM"};function _v(s){return xv[s.shadowMapType]||"SHADOWMAP_TYPE_BASIC"}var yv={[us]:"ENVMAP_TYPE_CUBE",[Os]:"ENVMAP_TYPE_CUBE",[Ha]:"ENVMAP_TYPE_CUBE_UV"};function vv(s){return s.envMap===!1?"ENVMAP_TYPE_CUBE":yv[s.envMapMode]||"ENVMAP_TYPE_CUBE"}var Mv={[Os]:"ENVMAP_MODE_REFRACTION"};function Sv(s){return s.envMap===!1?"ENVMAP_MODE_REFLECTION":Mv[s.envMapMode]||"ENVMAP_MODE_REFLECTION"}var bv={[Hh]:"ENVMAP_BLENDING_MULTIPLY",[Ff]:"ENVMAP_BLENDING_MIX",[Of]:"ENVMAP_BLENDING_ADD"};function Tv(s){return s.envMap===!1?"ENVMAP_BLENDING_NONE":bv[s.combine]||"ENVMAP_BLENDING_NONE"}function wv(s){let e=s.envMapCubeUVHeight;if(e===null)return null;let t=Math.log2(e)-2,n=1/e;return{texelWidth:1/(3*Math.max(Math.pow(2,t),112)),texelHeight:n,maxMip:t}}function Av(s,e,t,n){let i=s.getContext(),r=t.defines,a=t.vertexShader,o=t.fragmentShader,c=_v(t),l=vv(t),h=Sv(t),u=Tv(t),d=wv(t),p=cv(t),g=hv(r),v=i.createProgram(),f,m,_=t.glslVersion?"#version "+t.glslVersion+`
`:"";t.isRawShaderMaterial?(f=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g].filter(Qa).join(`
`),f.length>0&&(f+=`
`),m=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g].filter(Qa).join(`
`),m.length>0&&(m+=`
`)):(f=[bp(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g,t.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",t.batching?"#define USE_BATCHING":"",t.batchingColor?"#define USE_BATCHING_COLOR":"",t.instancing?"#define USE_INSTANCING":"",t.instancingColor?"#define USE_INSTANCING_COLOR":"",t.instancingMorph?"#define USE_INSTANCING_MORPH":"",t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.map?"#define USE_MAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+h:"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.displacementMap?"#define USE_DISPLACEMENTMAP":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.mapUv?"#define MAP_UV "+t.mapUv:"",t.alphaMapUv?"#define ALPHAMAP_UV "+t.alphaMapUv:"",t.lightMapUv?"#define LIGHTMAP_UV "+t.lightMapUv:"",t.aoMapUv?"#define AOMAP_UV "+t.aoMapUv:"",t.emissiveMapUv?"#define EMISSIVEMAP_UV "+t.emissiveMapUv:"",t.bumpMapUv?"#define BUMPMAP_UV "+t.bumpMapUv:"",t.normalMapUv?"#define NORMALMAP_UV "+t.normalMapUv:"",t.displacementMapUv?"#define DISPLACEMENTMAP_UV "+t.displacementMapUv:"",t.metalnessMapUv?"#define METALNESSMAP_UV "+t.metalnessMapUv:"",t.roughnessMapUv?"#define ROUGHNESSMAP_UV "+t.roughnessMapUv:"",t.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+t.anisotropyMapUv:"",t.clearcoatMapUv?"#define CLEARCOATMAP_UV "+t.clearcoatMapUv:"",t.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+t.clearcoatNormalMapUv:"",t.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+t.clearcoatRoughnessMapUv:"",t.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+t.iridescenceMapUv:"",t.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+t.iridescenceThicknessMapUv:"",t.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+t.sheenColorMapUv:"",t.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+t.sheenRoughnessMapUv:"",t.specularMapUv?"#define SPECULARMAP_UV "+t.specularMapUv:"",t.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+t.specularColorMapUv:"",t.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+t.specularIntensityMapUv:"",t.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+t.transmissionMapUv:"",t.thicknessMapUv?"#define THICKNESSMAP_UV "+t.thicknessMapUv:"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexNormals?"#define HAS_NORMAL":"",t.vertexColors?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.flatShading?"#define FLAT_SHADED":"",t.skinning?"#define USE_SKINNING":"",t.morphTargets?"#define USE_MORPHTARGETS":"",t.morphNormals&&t.flatShading===!1?"#define USE_MORPHNORMALS":"",t.morphColors?"#define USE_MORPHCOLORS":"",t.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+t.morphTextureStride:"",t.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+t.morphTargetsCount:"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+c:"",t.sizeAttenuation?"#define USE_SIZEATTENUATION":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",t.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(Qa).join(`
`),m=[bp(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g,t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",t.map?"#define USE_MAP":"",t.matcap?"#define USE_MATCAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+l:"",t.envMap?"#define "+h:"",t.envMap?"#define "+u:"",d?"#define CUBEUV_TEXEL_WIDTH "+d.texelWidth:"",d?"#define CUBEUV_TEXEL_HEIGHT "+d.texelHeight:"",d?"#define CUBEUV_MAX_MIP "+d.maxMip+".0":"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.packedNormalMap?"#define USE_PACKED_NORMALMAP":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoat?"#define USE_CLEARCOAT":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.dispersion?"#define USE_DISPERSION":"",t.retroreflection?"#define USE_RETROREFLECTION":"",t.iridescence?"#define USE_IRIDESCENCE":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaTest?"#define USE_ALPHATEST":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.sheen?"#define USE_SHEEN":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors||t.instancingColor?"#define USE_COLOR":"",t.vertexAlphas||t.batchingColor?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.gradientMap?"#define USE_GRADIENTMAP":"",t.flatShading?"#define FLAT_SHADED":"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+c:"",t.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.numLightProbeGrids>0?"#define USE_LIGHT_PROBES_GRID":"",t.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",t.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",t.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",t.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",t.toneMapping!==ri?"#define TONE_MAPPING":"",t.toneMapping!==ri?at.tonemapping_pars_fragment:"",t.toneMapping!==ri?ov("toneMapping",t.toneMapping):"",t.dithering?"#define DITHERING":"",t.opaque?"#define OPAQUE":"",at.colorspace_pars_fragment,rv("linearToOutputTexel",t.outputColorSpace),lv(),t.useDepthPacking?"#define DEPTH_PACKING "+t.depthPacking:"",`
`].filter(Qa).join(`
`)),a=xu(a),a=vp(a,t),a=Mp(a,t),o=xu(o),o=vp(o,t),o=Mp(o,t),a=Sp(a),o=Sp(o),t.isRawShaderMaterial!==!0&&(_=`#version 300 es
`,f=[p,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+f,m=["#define varying in",t.glslVersion===eu?"":"layout(location = 0) out highp vec4 pc_fragColor;",t.glslVersion===eu?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+m);let b=_+f+a,x=_+m+o,T=xp(i,i.VERTEX_SHADER,b),S=xp(i,i.FRAGMENT_SHADER,x);i.attachShader(v,T),i.attachShader(v,S),t.index0AttributeName!==void 0?i.bindAttribLocation(v,0,t.index0AttributeName):t.hasPositionAttribute===!0&&i.bindAttribLocation(v,0,"position"),i.linkProgram(v);function A(L){if(s.debug.checkShaderErrors){let F=i.getProgramInfoLog(v)||"",V=i.getShaderInfoLog(T)||"",D=i.getShaderInfoLog(S)||"",B=F.trim(),X=V.trim(),W=D.trim(),re=!0,q=!0;if(i.getProgramParameter(v,i.LINK_STATUS)===!1)if(re=!1,typeof s.debug.onShaderError=="function")s.debug.onShaderError(i,v,T,S);else{let j=yp(i,T,"vertex"),te=yp(i,S,"fragment");He("WebGLProgram: Shader Error "+i.getError()+" - VALIDATE_STATUS "+i.getProgramParameter(v,i.VALIDATE_STATUS)+`

Material Name: `+L.name+`
Material Type: `+L.type+`

Program Info Log: `+B+`
`+j+`
`+te)}else B!==""?Le("WebGLProgram: Program Info Log:",B):(X===""||W==="")&&(q=!1);q&&(L.diagnostics={runnable:re,programLog:B,vertexShader:{log:X,prefix:f},fragmentShader:{log:W,prefix:m}})}i.deleteShader(T),i.deleteShader(S),y=new Br(i,v),E=uv(i,v)}let y;this.getUniforms=function(){return y===void 0&&A(this),y};let E;this.getAttributes=function(){return E===void 0&&A(this),E};let I=t.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return I===!1&&(I=i.getProgramParameter(v,tv)),I},this.destroy=function(){n.releaseStatesOfProgram(this),i.deleteProgram(v),this.program=void 0},this.type=t.shaderType,this.name=t.shaderName,this.id=nv++,this.cacheKey=e,this.usedTimes=1,this.program=v,this.vertexShader=T,this.fragmentShader=S,this}var Ev=0,_u=class{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e,t,n){let i=this._getShaderCacheForMaterial(e);return i.has(t)===!1&&(i.add(t),t.usedTimes++),i.has(n)===!1&&(i.add(n),n.usedTimes++),this}remove(e){let t=this.materialCache.get(e);for(let n of t)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(e),this}getVertexShaderStage(e){return this._getShaderStage(e.vertexShader)}getFragmentShaderStage(e){return this._getShaderStage(e.fragmentShader)}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){let t=this.materialCache,n=t.get(e);return n===void 0&&(n=new Set,t.set(e,n)),n}_getShaderStage(e){let t=this.shaderCache,n=t.get(e);return n===void 0&&(n=new yu(e),t.set(e,n)),n}},yu=class{constructor(e){this.id=Ev++,this.code=e,this.usedTimes=0}};function Cv(s){return s===fs||s===Ka||s===Za}function Rv(s,e,t,n,i,r){let a=new ca,o=new _u,c=new Set,l=[],h=new Map,u=n.logarithmicDepthBuffer,d=n.precision,p={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distance",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function g(y){return c.add(y),y===0?"uv":`uv${y}`}function v(y,E,I,L,F,V){let D=L.fog,B=F.geometry,X=y.isMeshStandardMaterial||y.isMeshLambertMaterial||y.isMeshPhongMaterial?L.environment:null,W=y.isMeshStandardMaterial||y.isMeshLambertMaterial&&!y.envMap||y.isMeshPhongMaterial&&!y.envMap,re=e.get(y.envMap||X,W),q=re&&re.mapping===Ha?re.image.height:null,j=p[y.type];y.precision!==null&&(d=n.getMaxPrecision(y.precision),d!==y.precision&&Le("WebGLProgram.getParameters:",y.precision,"not supported, using",d,"instead."));let te=B.morphAttributes.position||B.morphAttributes.normal||B.morphAttributes.color,Ne=te!==void 0?te.length:0,Ae=0;B.morphAttributes.position!==void 0&&(Ae=1),B.morphAttributes.normal!==void 0&&(Ae=2),B.morphAttributes.color!==void 0&&(Ae=3);let vt,ct,mt,Z;if(j){let Dt=Ei[j];vt=Dt.vertexShader,ct=Dt.fragmentShader}else{vt=y.vertexShader,ct=y.fragmentShader;let Dt=o.getVertexShaderStage(y),St=o.getFragmentShaderStage(y);o.update(y,Dt,St),mt=Dt.id,Z=St.id}let Q=s.getRenderTarget(),_e=s.state.buffers.depth.getReversed(),We=F.isInstancedMesh===!0,be=F.isBatchedMesh===!0,Xe=!!y.map,Tt=!!y.matcap,ee=!!re,ae=!!y.aoMap,oe=!!y.lightMap,le=!!y.bumpMap&&y.wireframe===!1,ue=!!y.normalMap,ze=!!y.displacementMap,Be=!!y.emissiveMap,qe=!!y.metalnessMap,$e=!!y.roughnessMap,P=y.anisotropy>0,Mt=y.clearcoat>0,ht=y.dispersion>0,C=y.retroreflectivity>0,M=y.iridescence>0,O=y.sheen>0,G=y.transmission>0,Y=P&&!!y.anisotropyMap,ce=Mt&&!!y.clearcoatMap,he=Mt&&!!y.clearcoatNormalMap,K=Mt&&!!y.clearcoatRoughnessMap,$=M&&!!y.iridescenceMap,de=M&&!!y.iridescenceThicknessMap,De=O&&!!y.sheenColorMap,ge=O&&!!y.sheenRoughnessMap,fe=!!y.specularMap,Ue=!!y.specularColorMap,Ge=!!y.specularIntensityMap,et=G&&!!y.transmissionMap,U=G&&!!y.thicknessMap,pe=!!y.gradientMap,J=!!y.alphaMap,me=y.alphaTest>0,Se=!!y.alphaHash,ie=!!y.extensions,Fe=ri;y.toneMapped&&(Q===null||Q.isXRRenderTarget===!0)&&(Fe=s.toneMapping);let Ie={shaderID:j,shaderType:y.type,shaderName:y.name,vertexShader:vt,fragmentShader:ct,defines:y.defines,customVertexShaderID:mt,customFragmentShaderID:Z,isRawShaderMaterial:y.isRawShaderMaterial===!0,glslVersion:y.glslVersion,precision:d,batching:be,batchingColor:be&&F._colorsTexture!==null,instancing:We,instancingColor:We&&F.instanceColor!==null,instancingMorph:We&&F.morphTexture!==null,outputColorSpace:Q===null?s.outputColorSpace:Q.isXRRenderTarget===!0?Q.texture.colorSpace:it.workingColorSpace,alphaToCoverage:!!y.alphaToCoverage,map:Xe,matcap:Tt,envMap:ee,envMapMode:ee&&re.mapping,envMapCubeUVHeight:q,aoMap:ae,lightMap:oe,bumpMap:le,normalMap:ue,displacementMap:ze,emissiveMap:Be,normalMapObjectSpace:ue&&y.normalMapType===Gf,normalMapTangentSpace:ue&&y.normalMapType===oc,packedNormalMap:ue&&y.normalMapType===oc&&Cv(y.normalMap.format),metalnessMap:qe,roughnessMap:$e,anisotropy:P,anisotropyMap:Y,clearcoat:Mt,clearcoatMap:ce,clearcoatNormalMap:he,clearcoatRoughnessMap:K,dispersion:ht,retroreflection:C,iridescence:M,iridescenceMap:$,iridescenceThicknessMap:de,sheen:O,sheenColorMap:De,sheenRoughnessMap:ge,specularMap:fe,specularColorMap:Ue,specularIntensityMap:Ge,transmission:G,transmissionMap:et,thicknessMap:U,gradientMap:pe,opaque:y.transparent===!1&&y.blending===Ir&&y.alphaToCoverage===!1,alphaMap:J,alphaTest:me,alphaHash:Se,combine:y.combine,mapUv:Xe&&g(y.map.channel),aoMapUv:ae&&g(y.aoMap.channel),lightMapUv:oe&&g(y.lightMap.channel),bumpMapUv:le&&g(y.bumpMap.channel),normalMapUv:ue&&g(y.normalMap.channel),displacementMapUv:ze&&g(y.displacementMap.channel),emissiveMapUv:Be&&g(y.emissiveMap.channel),metalnessMapUv:qe&&g(y.metalnessMap.channel),roughnessMapUv:$e&&g(y.roughnessMap.channel),anisotropyMapUv:Y&&g(y.anisotropyMap.channel),clearcoatMapUv:ce&&g(y.clearcoatMap.channel),clearcoatNormalMapUv:he&&g(y.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:K&&g(y.clearcoatRoughnessMap.channel),iridescenceMapUv:$&&g(y.iridescenceMap.channel),iridescenceThicknessMapUv:de&&g(y.iridescenceThicknessMap.channel),sheenColorMapUv:De&&g(y.sheenColorMap.channel),sheenRoughnessMapUv:ge&&g(y.sheenRoughnessMap.channel),specularMapUv:fe&&g(y.specularMap.channel),specularColorMapUv:Ue&&g(y.specularColorMap.channel),specularIntensityMapUv:Ge&&g(y.specularIntensityMap.channel),transmissionMapUv:et&&g(y.transmissionMap.channel),thicknessMapUv:U&&g(y.thicknessMap.channel),alphaMapUv:J&&g(y.alphaMap.channel),vertexTangents:!!B.attributes.tangent&&(ue||P),vertexNormals:!!B.attributes.normal,vertexColors:y.vertexColors,vertexAlphas:y.vertexColors===!0&&!!B.attributes.color&&B.attributes.color.itemSize===4,pointsUvs:F.isPoints===!0&&!!B.attributes.uv&&(Xe||J),fog:!!D,useFog:y.fog===!0,fogExp2:!!D&&D.isFogExp2,flatShading:y.wireframe===!1&&(y.flatShading===!0||B.attributes.normal===void 0&&ue===!1&&(y.isMeshLambertMaterial||y.isMeshPhongMaterial||y.isMeshStandardMaterial||y.isMeshPhysicalMaterial)),sizeAttenuation:y.sizeAttenuation===!0,logarithmicDepthBuffer:u,reversedDepthBuffer:_e,skinning:F.isSkinnedMesh===!0,hasPositionAttribute:B.attributes.position!==void 0,morphTargets:B.morphAttributes.position!==void 0,morphNormals:B.morphAttributes.normal!==void 0,morphColors:B.morphAttributes.color!==void 0,morphTargetsCount:Ne,morphTextureStride:Ae,numSunLights:E.sun.length,numDirLights:E.directional.length,numPointLights:E.point.length,numSpotLights:E.spot.length,numSpotLightMaps:E.spotLightMap.length,numRectAreaLights:E.rectArea.length,numHemiLights:E.hemi.length,numSunLightShadows:E.sunShadowMap.length,numDirLightShadows:E.directionalShadowMap.length,numPointLightShadows:E.pointShadowMap.length,numSpotLightShadows:E.spotShadowMap.length,numSpotLightShadowsWithMaps:E.numSpotLightShadowsWithMaps,numLightProbes:E.numLightProbes,numLightProbeGrids:V.length,numClippingPlanes:r.numPlanes,numClipIntersection:r.numIntersection,dithering:y.dithering,shadowMapEnabled:s.shadowMap.enabled&&I.length>0,shadowMapType:s.shadowMap.type,toneMapping:Fe,decodeVideoTexture:Xe&&y.map.isVideoTexture===!0&&it.getTransfer(y.map.colorSpace)===_t,decodeVideoTextureEmissive:Be&&y.emissiveMap.isVideoTexture===!0&&it.getTransfer(y.emissiveMap.colorSpace)===_t,premultipliedAlpha:y.premultipliedAlpha,doubleSided:y.side===st,flipSided:y.side===qt,useDepthPacking:y.depthPacking>=0,depthPacking:y.depthPacking||0,index0AttributeName:y.index0AttributeName,extensionClipCullDistance:ie&&y.extensions.clipCullDistance===!0&&t.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(ie&&y.extensions.multiDraw===!0||be)&&t.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:t.has("KHR_parallel_shader_compile"),customProgramCacheKey:y.customProgramCacheKey()};return Ie.vertexUv1s=c.has(1),Ie.vertexUv2s=c.has(2),Ie.vertexUv3s=c.has(3),c.clear(),Ie}function f(y){let E=[];if(y.shaderID?E.push(y.shaderID):(E.push(y.customVertexShaderID),E.push(y.customFragmentShaderID)),y.defines!==void 0)for(let I in y.defines)E.push(I),E.push(y.defines[I]);return y.isRawShaderMaterial===!1&&(m(E,y),_(E,y),E.push(s.outputColorSpace)),E.push(y.customProgramCacheKey),E.join()}function m(y,E){y.push(E.precision),y.push(E.outputColorSpace),y.push(E.envMapMode),y.push(E.envMapCubeUVHeight),y.push(E.mapUv),y.push(E.alphaMapUv),y.push(E.lightMapUv),y.push(E.aoMapUv),y.push(E.bumpMapUv),y.push(E.normalMapUv),y.push(E.displacementMapUv),y.push(E.emissiveMapUv),y.push(E.metalnessMapUv),y.push(E.roughnessMapUv),y.push(E.anisotropyMapUv),y.push(E.clearcoatMapUv),y.push(E.clearcoatNormalMapUv),y.push(E.clearcoatRoughnessMapUv),y.push(E.iridescenceMapUv),y.push(E.iridescenceThicknessMapUv),y.push(E.sheenColorMapUv),y.push(E.sheenRoughnessMapUv),y.push(E.specularMapUv),y.push(E.specularColorMapUv),y.push(E.specularIntensityMapUv),y.push(E.transmissionMapUv),y.push(E.thicknessMapUv),y.push(E.combine),y.push(E.fogExp2),y.push(E.sizeAttenuation),y.push(E.morphTargetsCount),y.push(E.morphAttributeCount),y.push(E.numSunLights),y.push(E.numDirLights),y.push(E.numPointLights),y.push(E.numSpotLights),y.push(E.numSpotLightMaps),y.push(E.numHemiLights),y.push(E.numRectAreaLights),y.push(E.numSunLightShadows),y.push(E.numDirLightShadows),y.push(E.numPointLightShadows),y.push(E.numSpotLightShadows),y.push(E.numSpotLightShadowsWithMaps),y.push(E.numLightProbes),y.push(E.shadowMapType),y.push(E.toneMapping),y.push(E.numClippingPlanes),y.push(E.numClipIntersection),y.push(E.depthPacking)}function _(y,E){a.disableAll(),E.instancing&&a.enable(0),E.instancingColor&&a.enable(1),E.instancingMorph&&a.enable(2),E.matcap&&a.enable(3),E.envMap&&a.enable(4),E.normalMapObjectSpace&&a.enable(5),E.normalMapTangentSpace&&a.enable(6),E.clearcoat&&a.enable(7),E.iridescence&&a.enable(8),E.alphaTest&&a.enable(9),E.vertexColors&&a.enable(10),E.vertexAlphas&&a.enable(11),E.vertexUv1s&&a.enable(12),E.vertexUv2s&&a.enable(13),E.vertexUv3s&&a.enable(14),E.vertexTangents&&a.enable(15),E.anisotropy&&a.enable(16),E.alphaHash&&a.enable(17),E.batching&&a.enable(18),E.dispersion&&a.enable(19),E.retroreflection&&a.enable(24),E.batchingColor&&a.enable(20),E.gradientMap&&a.enable(21),E.packedNormalMap&&a.enable(22),E.vertexNormals&&a.enable(23),y.push(a.mask),a.disableAll(),E.fog&&a.enable(0),E.useFog&&a.enable(1),E.flatShading&&a.enable(2),E.logarithmicDepthBuffer&&a.enable(3),E.reversedDepthBuffer&&a.enable(4),E.skinning&&a.enable(5),E.morphTargets&&a.enable(6),E.morphNormals&&a.enable(7),E.morphColors&&a.enable(8),E.premultipliedAlpha&&a.enable(9),E.shadowMapEnabled&&a.enable(10),E.doubleSided&&a.enable(11),E.flipSided&&a.enable(12),E.useDepthPacking&&a.enable(13),E.dithering&&a.enable(14),E.transmission&&a.enable(15),E.sheen&&a.enable(16),E.opaque&&a.enable(17),E.pointsUvs&&a.enable(18),E.decodeVideoTexture&&a.enable(19),E.decodeVideoTextureEmissive&&a.enable(20),E.alphaToCoverage&&a.enable(21),E.numLightProbeGrids>0&&a.enable(22),E.hasPositionAttribute&&a.enable(23),y.push(a.mask)}function b(y){let E=p[y.type],I;if(E){let L=Ei[E];I=qi.clone(L.uniforms)}else I=y.uniforms;return I}function x(y,E){let I=h.get(E);return I!==void 0?++I.usedTimes:(I=new Av(s,E,y,i),l.push(I),h.set(E,I)),I}function T(y){if(--y.usedTimes===0){let E=l.indexOf(y);l[E]=l[l.length-1],l.pop(),h.delete(y.cacheKey),y.destroy()}}function S(y){o.remove(y)}function A(){o.dispose()}return{getParameters:v,getProgramCacheKey:f,getUniforms:b,acquireProgram:x,releaseProgram:T,releaseShaderCache:S,programs:l,dispose:A}}function Iv(){let s=new WeakMap;function e(a){return s.has(a)}function t(a){let o=s.get(a);return o===void 0&&(o={},s.set(a,o)),o}function n(a){s.delete(a)}function i(a,o,c){s.get(a)[o]=c}function r(){s=new WeakMap}return{has:e,get:t,remove:n,update:i,dispose:r}}function Pv(s,e){return s.groupOrder!==e.groupOrder?s.groupOrder-e.groupOrder:s.renderOrder!==e.renderOrder?s.renderOrder-e.renderOrder:s.material.id!==e.material.id?s.material.id-e.material.id:s.materialVariant!==e.materialVariant?s.materialVariant-e.materialVariant:s.z!==e.z?s.z-e.z:s.id-e.id}function Tp(s,e){return s.groupOrder!==e.groupOrder?s.groupOrder-e.groupOrder:s.renderOrder!==e.renderOrder?s.renderOrder-e.renderOrder:s.z!==e.z?e.z-s.z:s.id-e.id}function wp(){let s=[],e=0,t=[],n=[],i=[];function r(){e=0,t.length=0,n.length=0,i.length=0}function a(d){let p=0;return d.isInstancedMesh&&(p+=2),d.isSkinnedMesh&&(p+=1),p}function o(d,p,g,v,f,m){let _=s[e];return _===void 0?(_={id:d.id,object:d,geometry:p,material:g,materialVariant:a(d),groupOrder:v,renderOrder:d.renderOrder,z:f,group:m},s[e]=_):(_.id=d.id,_.object=d,_.geometry=p,_.material=g,_.materialVariant=a(d),_.groupOrder=v,_.renderOrder=d.renderOrder,_.z=f,_.group=m),e++,_}function c(d,p,g,v,f,m,_){_.reversedDepth===!0&&(f=-f);let b=o(d,p,g,v,f,m);g.transmission>0?n.push(b):g.transparent===!0?i.push(b):t.push(b)}function l(d,p,g,v,f,m){let _=o(d,p,g,v,f,m);g.transmission>0?n.unshift(_):g.transparent===!0?i.unshift(_):t.unshift(_)}function h(d,p){t.length>1&&t.sort(d||Pv),n.length>1&&n.sort(p||Tp),i.length>1&&i.sort(p||Tp)}function u(){for(let d=e,p=s.length;d<p;d++){let g=s[d];if(g.id===null)break;g.id=null,g.object=null,g.geometry=null,g.material=null,g.group=null}}return{opaque:t,transmissive:n,transparent:i,init:r,push:c,unshift:l,finish:u,sort:h}}function Lv(){let s=new WeakMap;function e(n,i){let r=s.get(n),a;return r===void 0?(a=new wp,s.set(n,[a])):i>=r.length?(a=new wp,r.push(a)):a=r[i],a}function t(){s=new WeakMap}return{get:e,dispose:t}}function Nv(){let s={};return{get:function(e){if(s[e.id]!==void 0)return s[e.id];let t;switch(e.type){case"SunLight":case"DirectionalLight":t={direction:new R,color:new Me};break;case"SpotLight":t={position:new R,direction:new R,color:new Me,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":t={position:new R,color:new Me,distance:0,decay:0};break;case"HemisphereLight":t={direction:new R,skyColor:new Me,groundColor:new Me};break;case"RectAreaLight":t={color:new Me,position:new R,halfWidth:new R,halfHeight:new R};break}return s[e.id]=t,t}}}function Dv(){let s={};return{get:function(e){if(s[e.id]!==void 0)return s[e.id];let t;switch(e.type){case"SunLight":case"DirectionalLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new ne};break;case"SpotLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new ne};break;case"PointLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new ne,shadowCameraNear:1,shadowCameraFar:1e3};break}return s[e.id]=t,t}}}var Uv=0;function Fv(s,e){return(e.castShadow?2:0)-(s.castShadow?2:0)+(e.map?1:0)-(s.map?1:0)}function Ov(s){let e=new Nv,t=Dv(),n={version:0,hash:{sunLength:-1,directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numSunShadows:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],sun:[],sunShadow:[],sunShadowMap:[],sunShadowMatrix:[],sunShadowCascade:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let l=0;l<9;l++)n.probe.push(new R);let i=new R,r=new je,a=new je;function o(l){let h=0,u=0,d=0;for(let F=0;F<9;F++)n.probe[F].set(0,0,0);let p=0,g=0,v=0,f=0,m=0,_=0,b=0,x=0,T=0,S=0,A=0,y=0,E=0,I=0;l.sort(Fv);for(let F=0,V=l.length;F<V;F++){let D=l[F],B=D.color,X=D.intensity,W=D.distance,re=null;if(D.shadow&&D.shadow.map&&(D.shadow.map.texture.format===fs?re=D.shadow.map.texture:re=D.shadow.map.depthTexture||D.shadow.map.texture),D.isAmbientLight)h+=B.r*X,u+=B.g*X,d+=B.b*X;else if(D.isLightProbe){for(let q=0;q<9;q++)n.probe[q].addScaledVector(D.sh.coefficients[q],X);I++}else if(D.isSunLight){let q=e.get(D);if(q.color.copy(D.color).multiplyScalar(D.intensity),D.castShadow){let j=D.shadow,te=t.get(D);te.shadowIntensity=j.intensity,te.shadowBias=j.bias,te.shadowNormalBias=j.normalBias,te.shadowRadius=j.radius,te.shadowMapSize.copy(j.mapSize).multiply(j.getFrameExtents()),n.sunShadow[g]=te,n.sunShadowMap[g]=re;let Ne=j.getViewportCount();for(let Ae=0;Ae<Ne;Ae++)n.sunShadowMatrix[v+Ae]=j.getMatrix(Ae),n.sunShadowCascade[v+Ae]=j._cascadeData[Ae];v+=Ne,g++}n.sun[p]=q,p++}else if(D.isDirectionalLight){let q=e.get(D);if(q.color.copy(D.color).multiplyScalar(D.intensity),D.castShadow){let j=D.shadow,te=t.get(D);te.shadowIntensity=j.intensity,te.shadowBias=j.bias,te.shadowNormalBias=j.normalBias,te.shadowRadius=j.radius,te.shadowMapSize=j.mapSize,n.directionalShadow[f]=te,n.directionalShadowMap[f]=re,n.directionalShadowMatrix[f]=D.shadow.matrix,T++}n.directional[f]=q,f++}else if(D.isSpotLight){let q=e.get(D);q.position.setFromMatrixPosition(D.matrixWorld),q.color.copy(B).multiplyScalar(X),q.distance=W,q.coneCos=Math.cos(D.angle),q.penumbraCos=Math.cos(D.angle*(1-D.penumbra)),q.decay=D.decay,n.spot[_]=q;let j=D.shadow;if(D.map&&(n.spotLightMap[y]=D.map,y++,j.updateMatrices(D),D.castShadow&&E++),n.spotLightMatrix[_]=j.matrix,D.castShadow){let te=t.get(D);te.shadowIntensity=j.intensity,te.shadowBias=j.bias,te.shadowNormalBias=j.normalBias,te.shadowRadius=j.radius,te.shadowMapSize=j.mapSize,n.spotShadow[_]=te,n.spotShadowMap[_]=re,A++}_++}else if(D.isRectAreaLight){let q=e.get(D);q.color.copy(B).multiplyScalar(X),q.halfWidth.set(D.width*.5,0,0),q.halfHeight.set(0,D.height*.5,0),n.rectArea[b]=q,b++}else if(D.isPointLight){let q=e.get(D);if(q.color.copy(D.color).multiplyScalar(D.intensity),q.distance=D.distance,q.decay=D.decay,D.castShadow){let j=D.shadow,te=t.get(D);te.shadowIntensity=j.intensity,te.shadowBias=j.bias,te.shadowNormalBias=j.normalBias,te.shadowRadius=j.radius,te.shadowMapSize=j.mapSize,te.shadowCameraNear=j.camera.near,te.shadowCameraFar=j.camera.far,n.pointShadow[m]=te,n.pointShadowMap[m]=re,n.pointShadowMatrix[m]=D.shadow.matrix,S++}n.point[m]=q,m++}else if(D.isHemisphereLight){let q=e.get(D);q.skyColor.copy(D.color).multiplyScalar(X),q.groundColor.copy(D.groundColor).multiplyScalar(X),n.hemi[x]=q,x++}}b>0&&(s.has("OES_texture_float_linear")===!0?(n.rectAreaLTC1=xe.LTC_FLOAT_1,n.rectAreaLTC2=xe.LTC_FLOAT_2):(n.rectAreaLTC1=xe.LTC_HALF_1,n.rectAreaLTC2=xe.LTC_HALF_2)),n.ambient[0]=h,n.ambient[1]=u,n.ambient[2]=d;let L=n.hash;(L.sunLength!==p||L.directionalLength!==f||L.pointLength!==m||L.spotLength!==_||L.rectAreaLength!==b||L.hemiLength!==x||L.numSunShadows!==g||L.numDirectionalShadows!==T||L.numPointShadows!==S||L.numSpotShadows!==A||L.numSpotMaps!==y||L.numLightProbes!==I)&&(n.sun.length=p,n.directional.length=f,n.spot.length=_,n.rectArea.length=b,n.point.length=m,n.hemi.length=x,n.sunShadow.length=g,n.sunShadowMap.length=g,n.sunShadowMatrix.length=v,n.sunShadowCascade.length=v,n.directionalShadow.length=T,n.directionalShadowMap.length=T,n.directionalShadowMatrix.length=T,n.pointShadow.length=S,n.pointShadowMap.length=S,n.pointShadowMatrix.length=S,n.spotShadow.length=A,n.spotShadowMap.length=A,n.spotLightMatrix.length=A+y-E,n.spotLightMap.length=y,n.numSpotLightShadowsWithMaps=E,n.numLightProbes=I,L.sunLength=p,L.directionalLength=f,L.pointLength=m,L.spotLength=_,L.rectAreaLength=b,L.hemiLength=x,L.numSunShadows=g,L.numDirectionalShadows=T,L.numPointShadows=S,L.numSpotShadows=A,L.numSpotMaps=y,L.numLightProbes=I,n.version=Uv++)}function c(l,h){let u=0,d=0,p=0,g=0,v=0,f=0,m=h.matrixWorldInverse;for(let _=0,b=l.length;_<b;_++){let x=l[_];if(x.isSunLight){let T=n.sun[u];T.direction.setFromMatrixPosition(x.matrixWorld),T.direction.transformDirection(m),u++}else if(x.isDirectionalLight){let T=n.directional[d];T.direction.setFromMatrixPosition(x.matrixWorld),i.setFromMatrixPosition(x.target.matrixWorld),T.direction.sub(i),T.direction.transformDirection(m),d++}else if(x.isSpotLight){let T=n.spot[g];T.position.setFromMatrixPosition(x.matrixWorld),T.position.applyMatrix4(m),T.direction.setFromMatrixPosition(x.matrixWorld),i.setFromMatrixPosition(x.target.matrixWorld),T.direction.sub(i),T.direction.transformDirection(m),g++}else if(x.isRectAreaLight){let T=n.rectArea[v];T.position.setFromMatrixPosition(x.matrixWorld),T.position.applyMatrix4(m),a.identity(),r.copy(x.matrixWorld),r.premultiply(m),a.extractRotation(r),T.halfWidth.set(x.width*.5,0,0),T.halfHeight.set(0,x.height*.5,0),T.halfWidth.applyMatrix4(a),T.halfHeight.applyMatrix4(a),v++}else if(x.isPointLight){let T=n.point[p];T.position.setFromMatrixPosition(x.matrixWorld),T.position.applyMatrix4(m),p++}else if(x.isHemisphereLight){let T=n.hemi[f];T.direction.setFromMatrixPosition(x.matrixWorld),T.direction.transformDirection(m),f++}}}return{setup:o,setupView:c,state:n}}function Ap(s){let e=new Ov(s),t=[],n=[],i=[];function r(d){u.camera=d,t.length=0,n.length=0,i.length=0}function a(d){t.push(d)}function o(d){n.push(d)}function c(d){i.push(d)}function l(){e.setup(t)}function h(d){e.setupView(t,d)}let u={lightsArray:t,shadowsArray:n,lightProbeGridArray:i,camera:null,lights:e,transmissionRenderTarget:{},textureUnits:0};return{init:r,state:u,setupLights:l,setupLightsView:h,pushLight:a,pushShadow:o,pushLightProbeGrid:c}}function Bv(s){let e=new WeakMap;function t(i,r=0){let a=e.get(i),o;return a===void 0?(o=new Ap(s),e.set(i,[o])):r>=a.length?(o=new Ap(s),a.push(o)):o=a[r],o}function n(){e=new WeakMap}return{get:t,dispose:n}}var kv=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,zv=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ).rg;
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ).r;
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( max( 0.0, squared_mean - mean * mean ) );
	gl_FragColor = vec4( mean, std_dev, 0.0, 1.0 );
}`,Gv=[new R(1,0,0),new R(-1,0,0),new R(0,1,0),new R(0,-1,0),new R(0,0,1),new R(0,0,-1)],Vv=[new R(0,-1,0),new R(0,-1,0),new R(0,0,1),new R(0,0,-1),new R(0,-1,0),new R(0,-1,0)],Ep=new je,ja=new R,du=new R;function Hv(s,e,t){let n=new br,i=new ne,r=new ne,a=new At,o=new ul,c=new dl,l={},h=t.maxTextureSize,u={[wi]:qt,[qt]:wi,[st]:st},d=new Bt({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new ne},radius:{value:4}},vertexShader:kv,fragmentShader:zv}),p=d.clone();p.defines.HORIZONTAL_PASS=1;let g=new tt;g.setAttribute("position",new Ft(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));let v=new Ee(g,d),f=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Ds;let m=this.type;this.render=function(S,A,y){if(f.enabled===!1||f.autoUpdate===!1&&f.needsUpdate===!1||S.length===0)return;this.type===xf&&(Le("WebGLShadowMap: PCFSoftShadowMap has been removed. Using PCFShadowMap instead."),this.type=Ds);let E=s.getRenderTarget(),I=s.getActiveCubeFace(),L=s.getActiveMipmapLevel(),F=s.state;F.setBlending(Xn),F.buffers.depth.getReversed()===!0?F.buffers.color.setClear(0,0,0,0):F.buffers.color.setClear(1,1,1,1),F.buffers.depth.setTest(!0),F.setScissorTest(!1);let V=m!==this.type;V&&A.traverse(function(D){D.material&&(Array.isArray(D.material)?D.material.forEach(B=>B.needsUpdate=!0):D.material.needsUpdate=!0)});for(let D=0,B=S.length;D<B;D++){let X=S[D],W=X.shadow;if(W===void 0){Le("WebGLShadowMap:",X,"has no shadow.");continue}if(W.autoUpdate===!1&&W.needsUpdate===!1)continue;i.copy(W.mapSize);let re=W.getFrameExtents();i.multiply(re),r.copy(W.mapSize),(i.x>h||i.y>h)&&(i.x>h&&(r.x=Math.floor(h/re.x),i.x=r.x*re.x,W.mapSize.x=r.x),i.y>h&&(r.y=Math.floor(h/re.y),i.y=r.y*re.y,W.mapSize.y=r.y));let q=s.state.buffers.depth.getReversed();if(W.camera._reversedDepth=q,W.map===null||V===!0){if(W.map!==null&&(W.map.depthTexture!==null&&(W.map.depthTexture.dispose(),W.map.depthTexture=null),W.map.dispose()),this.type===Rr){if(X.isPointLight){Le("WebGLShadowMap: VSM shadow maps are not supported for PointLights. Use PCF or BasicShadowMap instead.");continue}W.map=new Jt(i.x,i.y,{format:fs,type:an,minFilter:Xt,magFilter:Xt,generateMipmaps:!1}),W.map.texture.name=X.name+".shadowMap",W.map.depthTexture=new as(i.x,i.y,Dn),W.map.depthTexture.name=X.name+".shadowMapDepth",W.map.depthTexture.format=yi,W.map.depthTexture.compareFunction=null,W.map.depthTexture.minFilter=Wt,W.map.depthTexture.magFilter=Wt}else X.isPointLight?(W.map=new fc(i.x),W.map.depthTexture=new rl(i.x,oi)):(W.map=new Jt(i.x,i.y),W.map.depthTexture=new as(i.x,i.y,oi)),W.map.depthTexture.name=X.name+".shadowMap",W.map.depthTexture.format=yi,this.type===Ds?(W.map.depthTexture.compareFunction=q?cc:lc,W.map.depthTexture.minFilter=Xt,W.map.depthTexture.magFilter=Xt):(W.map.depthTexture.compareFunction=null,W.map.depthTexture.minFilter=Wt,W.map.depthTexture.magFilter=Wt);W.camera.updateProjectionMatrix()}W.map.isWebGLCubeRenderTarget!==!0&&(W.map.width!==i.x||W.map.height!==i.y)&&W.map.setSize(i.x,i.y);let j=W.map.isWebGLCubeRenderTarget?6:W.getViewportCount();X.isPointLight!==!0&&W.updateMatrices(X,y);for(let te=0;te<j;te++){let Ne=W.getCamera(te);if(X.isPointLight){let Ae=W.camera,vt=W.matrix,ct=X.distance||Ae.far;ct!==Ae.far&&(Ae.far=ct,Ae.updateProjectionMatrix()),ja.setFromMatrixPosition(X.matrixWorld),Ae.position.copy(ja),du.copy(Ae.position),du.add(Gv[te]),Ae.up.copy(Vv[te]),Ae.lookAt(du),Ae.updateMatrixWorld(),vt.makeTranslation(-ja.x,-ja.y,-ja.z),Ep.multiplyMatrices(Ae.projectionMatrix,Ae.matrixWorldInverse),W._frustum.setFromProjectionMatrix(Ep,Ae.coordinateSystem,Ae.reversedDepth)}if(W.map.isWebGLCubeRenderTarget)s.setRenderTarget(W.map,te),s.clear();else{te===0&&(s.setRenderTarget(W.map),s.clear());let Ae=W.getViewport(te);a.set(r.x*Ae.x,r.y*Ae.y,r.x*Ae.z,r.y*Ae.w),F.viewport(a)}n=W.getFrustum(te),x(A,y,Ne,X,this.type)}W.isPointLightShadow!==!0&&this.type===Rr&&_(W,y),W.needsUpdate=!1}m=this.type,f.needsUpdate=!1,s.setRenderTarget(E,I,L)};function _(S,A){let y=e.update(v);d.defines.VSM_SAMPLES!==S.blurSamples&&(d.defines.VSM_SAMPLES=S.blurSamples,p.defines.VSM_SAMPLES=S.blurSamples,d.needsUpdate=!0,p.needsUpdate=!0),S.mapPass===null?S.mapPass=new Jt(i.x,i.y,{format:fs,type:an}):(S.mapPass.width!==S.map.width||S.mapPass.height!==S.map.height)&&S.mapPass.setSize(S.map.width,S.map.height),d.uniforms.shadow_pass.value=S.map.depthTexture,d.uniforms.resolution.value.set(S.map.width,S.map.height),d.uniforms.radius.value=S.radius,s.setRenderTarget(S.mapPass),s.clear(),s.renderBufferDirect(A,null,y,d,v,null),p.uniforms.shadow_pass.value=S.mapPass.texture,p.uniforms.resolution.value.set(S.map.width,S.map.height),p.uniforms.radius.value=S.radius,s.setRenderTarget(S.map),s.clear(),s.renderBufferDirect(A,null,y,p,v,null)}function b(S,A,y,E){let I=null,L=y.isPointLight===!0?S.customDistanceMaterial:S.customDepthMaterial;if(L!==void 0)I=L;else if(I=y.isPointLight===!0?c:o,s.localClippingEnabled&&A.clipShadows===!0&&Array.isArray(A.clippingPlanes)&&A.clippingPlanes.length!==0||A.displacementMap&&A.displacementScale!==0||A.alphaMap&&A.alphaTest>0||A.map&&A.alphaTest>0||A.alphaToCoverage===!0){let F=I.uuid,V=A.uuid,D=l[F];D===void 0&&(D={},l[F]=D);let B=D[V];B===void 0&&(B=I.clone(),D[V]=B,A.addEventListener("dispose",T)),I=B}if(I.visible=A.visible,I.wireframe=A.wireframe,E===Rr?I.side=A.shadowSide!==null?A.shadowSide:A.side:I.side=A.shadowSide!==null?A.shadowSide:u[A.side],I.alphaMap=A.alphaMap,I.alphaTest=A.alphaToCoverage===!0?.5:A.alphaTest,I.map=A.map,I.clipShadows=A.clipShadows,I.clippingPlanes=A.clippingPlanes,I.clipIntersection=A.clipIntersection,I.displacementMap=A.displacementMap,I.displacementScale=A.displacementScale,I.displacementBias=A.displacementBias,I.wireframeLinewidth=A.wireframeLinewidth,I.linewidth=A.linewidth,y.isPointLight===!0&&I.isMeshDistanceMaterial===!0){let F=s.properties.get(I);F.light=y}return I}function x(S,A,y,E,I){if(S.visible===!1)return;if(S.layers.test(A.layers)&&(S.isMesh||S.isLine||S.isPoints)&&(S.castShadow||S.receiveShadow&&I===Rr)&&(!S.frustumCulled||S.intersectsFrustum(n))){S.modelViewMatrix.multiplyMatrices(y.matrixWorldInverse,S.matrixWorld);let V=e.update(S),D=S.material;if(Array.isArray(D)){let B=V.groups;for(let X=0,W=B.length;X<W;X++){let re=B[X],q=D[re.materialIndex];if(q&&q.visible){let j=b(S,q,E,I);S.onBeforeShadow(s,S,A,y,V,j,re),s.renderBufferDirect(y,null,V,j,S,re),S.onAfterShadow(s,S,A,y,V,j,re)}}}else if(D.visible){let B=b(S,D,E,I);S.onBeforeShadow(s,S,A,y,V,B,null),s.renderBufferDirect(y,null,V,B,S,null),S.onAfterShadow(s,S,A,y,V,B,null)}}let F=S.children;for(let V=0,D=F.length;V<D;V++)x(F[V],A,y,E,I)}function T(S){S.target.removeEventListener("dispose",T);for(let y in l){let E=l[y],I=S.target.uuid;I in E&&(E[I].dispose(),delete E[I])}}}function Wv(s,e){function t(){let U=!1,pe=new At,J=null,me=new At(0,0,0,0);return{setMask:function(Se){J!==Se&&!U&&(s.colorMask(Se,Se,Se,Se),J=Se)},setLocked:function(Se){U=Se},setClear:function(Se,ie,Fe,Ie,Dt){Dt===!0&&(Se*=Ie,ie*=Ie,Fe*=Ie),pe.set(Se,ie,Fe,Ie),me.equals(pe)===!1&&(s.clearColor(Se,ie,Fe,Ie),me.copy(pe))},reset:function(){U=!1,J=null,me.set(-1,0,0,0)}}}function n(){let U=!1,pe=!1,J=null,me=null,Se=null;return{setReversed:function(ie){if(pe!==ie){let Fe=e.get("EXT_clip_control");ie?Fe.clipControlEXT(Fe.LOWER_LEFT_EXT,Fe.ZERO_TO_ONE_EXT):Fe.clipControlEXT(Fe.LOWER_LEFT_EXT,Fe.NEGATIVE_ONE_TO_ONE_EXT),pe=ie;let Ie=Se;Se=null,this.setClear(Ie)}},getReversed:function(){return pe},setTest:function(ie){ie?Q(s.DEPTH_TEST):_e(s.DEPTH_TEST)},setMask:function(ie){J!==ie&&!U&&(s.depthMask(ie),J=ie)},setFunc:function(ie){if(pe&&(ie=jf[ie]),me!==ie){switch(ie){case Yo:s.depthFunc(s.NEVER);break;case Ko:s.depthFunc(s.ALWAYS);break;case Zo:s.depthFunc(s.LESS);break;case pr:s.depthFunc(s.LEQUAL);break;case Jo:s.depthFunc(s.EQUAL);break;case $o:s.depthFunc(s.GEQUAL);break;case jo:s.depthFunc(s.GREATER);break;case Qo:s.depthFunc(s.NOTEQUAL);break;default:s.depthFunc(s.LEQUAL)}me=ie}},setLocked:function(ie){U=ie},setClear:function(ie){Se!==ie&&(Se=ie,pe&&(ie=1-ie),s.clearDepth(ie))},reset:function(){U=!1,J=null,me=null,Se=null,pe=!1}}}function i(){let U=!1,pe=null,J=null,me=null,Se=null,ie=null,Fe=null,Ie=null,Dt=null;return{setTest:function(St){U||(St?Q(s.STENCIL_TEST):_e(s.STENCIL_TEST))},setMask:function(St){pe!==St&&!U&&(s.stencilMask(St),pe=St)},setFunc:function(St,Jn,ui){(J!==St||me!==Jn||Se!==ui)&&(s.stencilFunc(St,Jn,ui),J=St,me=Jn,Se=ui)},setOp:function(St,Jn,ui){(ie!==St||Fe!==Jn||Ie!==ui)&&(s.stencilOp(St,Jn,ui),ie=St,Fe=Jn,Ie=ui)},setLocked:function(St){U=St},setClear:function(St){Dt!==St&&(s.clearStencil(St),Dt=St)},reset:function(){U=!1,pe=null,J=null,me=null,Se=null,ie=null,Fe=null,Ie=null,Dt=null}}}let r=new t,a=new n,o=new i,c=new WeakMap,l=new WeakMap,h={},u={},d={},p=new WeakMap,g=[],v=null,f=!1,m=null,_=null,b=null,x=null,T=null,S=null,A=null,y=new Me(0,0,0),E=0,I=!1,L=null,F=null,V=null,D=null,B=null,X=s.getParameter(s.MAX_COMBINED_TEXTURE_IMAGE_UNITS),W=!1,re=0,q=s.getParameter(s.VERSION);q.indexOf("WebGL")!==-1?(re=parseFloat(/^WebGL (\d)/.exec(q)[1]),W=re>=1):q.indexOf("OpenGL ES")!==-1&&(re=parseFloat(/^OpenGL ES (\d)/.exec(q)[1]),W=re>=2);let j=null,te={},Ne=s.getParameter(s.SCISSOR_BOX),Ae=s.getParameter(s.VIEWPORT),vt=new At().fromArray(Ne),ct=new At().fromArray(Ae);function mt(U,pe,J,me){let Se=new Uint8Array(4),ie=s.createTexture();s.bindTexture(U,ie),s.texParameteri(U,s.TEXTURE_MIN_FILTER,s.NEAREST),s.texParameteri(U,s.TEXTURE_MAG_FILTER,s.NEAREST);for(let Fe=0;Fe<J;Fe++)U===s.TEXTURE_3D||U===s.TEXTURE_2D_ARRAY?s.texImage3D(pe,0,s.RGBA,1,1,me,0,s.RGBA,s.UNSIGNED_BYTE,Se):s.texImage2D(pe+Fe,0,s.RGBA,1,1,0,s.RGBA,s.UNSIGNED_BYTE,Se);return ie}let Z={};Z[s.TEXTURE_2D]=mt(s.TEXTURE_2D,s.TEXTURE_2D,1),Z[s.TEXTURE_CUBE_MAP]=mt(s.TEXTURE_CUBE_MAP,s.TEXTURE_CUBE_MAP_POSITIVE_X,6),Z[s.TEXTURE_2D_ARRAY]=mt(s.TEXTURE_2D_ARRAY,s.TEXTURE_2D_ARRAY,1,1),Z[s.TEXTURE_3D]=mt(s.TEXTURE_3D,s.TEXTURE_3D,1,1),r.setClear(0,0,0,1),a.setClear(1),o.setClear(0),Q(s.DEPTH_TEST),a.setFunc(pr),le(!1),ue(Bh),Q(s.CULL_FACE),ae(Xn);function Q(U){h[U]!==!0&&(s.enable(U),h[U]=!0)}function _e(U){h[U]!==!1&&(s.disable(U),h[U]=!1)}function We(U,pe){return d[U]!==pe?(s.bindFramebuffer(U,pe),d[U]=pe,U===s.DRAW_FRAMEBUFFER&&(d[s.FRAMEBUFFER]=pe),U===s.FRAMEBUFFER&&(d[s.DRAW_FRAMEBUFFER]=pe),!0):!1}function be(U,pe){let J=g,me=!1;if(U){J=p.get(pe),J===void 0&&(J=[],p.set(pe,J));let Se=U.textures;if(J.length!==Se.length||J[0]!==s.COLOR_ATTACHMENT0){for(let ie=0,Fe=Se.length;ie<Fe;ie++)J[ie]=s.COLOR_ATTACHMENT0+ie;J.length=Se.length,me=!0}}else J[0]!==s.BACK&&(J[0]=s.BACK,me=!0);me&&s.drawBuffers(J)}function Xe(U){return v!==U?(s.useProgram(U),v=U,!0):!1}let Tt={[Us]:s.FUNC_ADD,[yf]:s.FUNC_SUBTRACT,[vf]:s.FUNC_REVERSE_SUBTRACT};Tt[Mf]=s.MIN,Tt[Sf]=s.MAX;let ee={[bf]:s.ZERO,[Tf]:s.ONE,[wf]:s.SRC_COLOR,[Gh]:s.SRC_ALPHA,[Pf]:s.SRC_ALPHA_SATURATE,[Rf]:s.DST_COLOR,[Ef]:s.DST_ALPHA,[Af]:s.ONE_MINUS_SRC_COLOR,[Vh]:s.ONE_MINUS_SRC_ALPHA,[If]:s.ONE_MINUS_DST_COLOR,[Cf]:s.ONE_MINUS_DST_ALPHA,[Lf]:s.CONSTANT_COLOR,[Nf]:s.ONE_MINUS_CONSTANT_COLOR,[Df]:s.CONSTANT_ALPHA,[Uf]:s.ONE_MINUS_CONSTANT_ALPHA};function ae(U,pe,J,me,Se,ie,Fe,Ie,Dt,St){if(U===Xn){f===!0&&(_e(s.BLEND),f=!1);return}if(f===!1&&(Q(s.BLEND),f=!0),U!==_f){if(U!==m||St!==I){if((_!==Us||T!==Us)&&(s.blendEquation(s.FUNC_ADD),_=Us,T=Us),St)switch(U){case Ir:s.blendFuncSeparate(s.ONE,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case dt:s.blendFunc(s.ONE,s.ONE);break;case kh:s.blendFuncSeparate(s.ZERO,s.ONE_MINUS_SRC_COLOR,s.ZERO,s.ONE);break;case zh:s.blendFuncSeparate(s.DST_COLOR,s.ONE_MINUS_SRC_ALPHA,s.ZERO,s.ONE);break;default:He("WebGLState: Invalid blending: ",U);break}else switch(U){case Ir:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case dt:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE,s.ONE,s.ONE);break;case kh:He("WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case zh:He("WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:He("WebGLState: Invalid blending: ",U);break}b=null,x=null,S=null,A=null,y.set(0,0,0),E=0,m=U,I=St}return}Se=Se||pe,ie=ie||J,Fe=Fe||me,(pe!==_||Se!==T)&&(s.blendEquationSeparate(Tt[pe],Tt[Se]),_=pe,T=Se),(J!==b||me!==x||ie!==S||Fe!==A)&&(s.blendFuncSeparate(ee[J],ee[me],ee[ie],ee[Fe]),b=J,x=me,S=ie,A=Fe),(Ie.equals(y)===!1||Dt!==E)&&(s.blendColor(Ie.r,Ie.g,Ie.b,Dt),y.copy(Ie),E=Dt),m=U,I=!1}function oe(U,pe){U.side===st?_e(s.CULL_FACE):Q(s.CULL_FACE);let J=U.side===qt;pe&&(J=!J),le(J),U.blending===Ir&&U.transparent===!1?ae(Xn):ae(U.blending,U.blendEquation,U.blendSrc,U.blendDst,U.blendEquationAlpha,U.blendSrcAlpha,U.blendDstAlpha,U.blendColor,U.blendAlpha,U.premultipliedAlpha),a.setFunc(U.depthFunc),a.setTest(U.depthTest),a.setMask(U.depthWrite),r.setMask(U.colorWrite);let me=U.stencilWrite;o.setTest(me),me&&(o.setMask(U.stencilWriteMask),o.setFunc(U.stencilFunc,U.stencilRef,U.stencilFuncMask),o.setOp(U.stencilFail,U.stencilZFail,U.stencilZPass)),Be(U.polygonOffset,U.polygonOffsetFactor,U.polygonOffsetUnits),U.alphaToCoverage===!0?Q(s.SAMPLE_ALPHA_TO_COVERAGE):_e(s.SAMPLE_ALPHA_TO_COVERAGE)}function le(U){L!==U&&(U?s.frontFace(s.CW):s.frontFace(s.CCW),L=U)}function ue(U){U!==mf?(Q(s.CULL_FACE),U!==F&&(U===Bh?s.cullFace(s.BACK):U===gf?s.cullFace(s.FRONT):s.cullFace(s.FRONT_AND_BACK))):_e(s.CULL_FACE),F=U}function ze(U){U!==V&&(W&&s.lineWidth(U),V=U)}function Be(U,pe,J){U?(Q(s.POLYGON_OFFSET_FILL),(D!==pe||B!==J)&&(D=pe,B=J,a.getReversed()&&(pe=-pe),s.polygonOffset(pe,J))):_e(s.POLYGON_OFFSET_FILL)}function qe(U){U?Q(s.SCISSOR_TEST):_e(s.SCISSOR_TEST)}function $e(U){U===void 0&&(U=s.TEXTURE0+X-1),j!==U&&(s.activeTexture(U),j=U)}function P(U,pe,J){J===void 0&&(j===null?J=s.TEXTURE0+X-1:J=j);let me=te[J];me===void 0&&(me={type:void 0,texture:void 0},te[J]=me),(me.type!==U||me.texture!==pe)&&(j!==J&&(s.activeTexture(J),j=J),s.bindTexture(U,pe||Z[U]),me.type=U,me.texture=pe)}function Mt(){let U=te[j];U!==void 0&&U.type!==void 0&&(s.bindTexture(U.type,null),U.type=void 0,U.texture=void 0)}function ht(){try{s.compressedTexImage2D(...arguments)}catch(U){He("WebGLState:",U)}}function C(){try{s.compressedTexImage3D(...arguments)}catch(U){He("WebGLState:",U)}}function M(){try{s.texSubImage2D(...arguments)}catch(U){He("WebGLState:",U)}}function O(){try{s.texSubImage3D(...arguments)}catch(U){He("WebGLState:",U)}}function G(){try{s.compressedTexSubImage2D(...arguments)}catch(U){He("WebGLState:",U)}}function Y(){try{s.compressedTexSubImage3D(...arguments)}catch(U){He("WebGLState:",U)}}function ce(){try{s.texStorage2D(...arguments)}catch(U){He("WebGLState:",U)}}function he(){try{s.texStorage3D(...arguments)}catch(U){He("WebGLState:",U)}}function K(){try{s.texImage2D(...arguments)}catch(U){He("WebGLState:",U)}}function $(){try{s.texImage3D(...arguments)}catch(U){He("WebGLState:",U)}}function de(U){return u[U]!==void 0?u[U]:s.getParameter(U)}function De(U,pe){u[U]!==pe&&(s.pixelStorei(U,pe),u[U]=pe)}function ge(U){vt.equals(U)===!1&&(s.scissor(U.x,U.y,U.z,U.w),vt.copy(U))}function fe(U){ct.equals(U)===!1&&(s.viewport(U.x,U.y,U.z,U.w),ct.copy(U))}function Ue(U,pe){let J=l.get(pe);J===void 0&&(J=new WeakMap,l.set(pe,J));let me=J.get(U);me===void 0&&(me=s.getUniformBlockIndex(pe,U.name),J.set(U,me))}function Ge(U,pe){let me=l.get(pe).get(U);c.get(pe)!==me&&(s.uniformBlockBinding(pe,me,U.__bindingPointIndex),c.set(pe,me))}function et(){s.disable(s.BLEND),s.disable(s.CULL_FACE),s.disable(s.DEPTH_TEST),s.disable(s.POLYGON_OFFSET_FILL),s.disable(s.SCISSOR_TEST),s.disable(s.STENCIL_TEST),s.disable(s.SAMPLE_ALPHA_TO_COVERAGE),s.blendEquation(s.FUNC_ADD),s.blendFunc(s.ONE,s.ZERO),s.blendFuncSeparate(s.ONE,s.ZERO,s.ONE,s.ZERO),s.blendColor(0,0,0,0),s.colorMask(!0,!0,!0,!0),s.clearColor(0,0,0,0),s.depthMask(!0),s.depthFunc(s.LESS),a.setReversed(!1),s.clearDepth(1),s.stencilMask(4294967295),s.stencilFunc(s.ALWAYS,0,4294967295),s.stencilOp(s.KEEP,s.KEEP,s.KEEP),s.clearStencil(0),s.cullFace(s.BACK),s.frontFace(s.CCW),s.polygonOffset(0,0),s.activeTexture(s.TEXTURE0),s.bindFramebuffer(s.FRAMEBUFFER,null),s.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),s.bindFramebuffer(s.READ_FRAMEBUFFER,null),s.useProgram(null),s.lineWidth(1),s.scissor(0,0,s.canvas.width,s.canvas.height),s.viewport(0,0,s.canvas.width,s.canvas.height),s.pixelStorei(s.PACK_ALIGNMENT,4),s.pixelStorei(s.UNPACK_ALIGNMENT,4),s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,!1),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,!1),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,s.BROWSER_DEFAULT_WEBGL),s.pixelStorei(s.PACK_ROW_LENGTH,0),s.pixelStorei(s.PACK_SKIP_PIXELS,0),s.pixelStorei(s.PACK_SKIP_ROWS,0),s.pixelStorei(s.UNPACK_ROW_LENGTH,0),s.pixelStorei(s.UNPACK_IMAGE_HEIGHT,0),s.pixelStorei(s.UNPACK_SKIP_PIXELS,0),s.pixelStorei(s.UNPACK_SKIP_ROWS,0),s.pixelStorei(s.UNPACK_SKIP_IMAGES,0),h={},u={},j=null,te={},d={},p=new WeakMap,g=[],v=null,f=!1,m=null,_=null,b=null,x=null,T=null,S=null,A=null,y=new Me(0,0,0),E=0,I=!1,L=null,F=null,V=null,D=null,B=null,vt.set(0,0,s.canvas.width,s.canvas.height),ct.set(0,0,s.canvas.width,s.canvas.height),r.reset(),a.reset(),o.reset()}return{buffers:{color:r,depth:a,stencil:o},enable:Q,disable:_e,bindFramebuffer:We,drawBuffers:be,useProgram:Xe,setBlending:ae,setMaterial:oe,setFlipSided:le,setCullFace:ue,setLineWidth:ze,setPolygonOffset:Be,setScissorTest:qe,activeTexture:$e,bindTexture:P,unbindTexture:Mt,compressedTexImage2D:ht,compressedTexImage3D:C,texImage2D:K,texImage3D:$,pixelStorei:De,getParameter:de,updateUBOMapping:Ue,uniformBlockBinding:Ge,texStorage2D:ce,texStorage3D:he,texSubImage2D:M,texSubImage3D:O,compressedTexSubImage2D:G,compressedTexSubImage3D:Y,scissor:ge,viewport:fe,reset:et}}function Xv(s,e,t,n,i,r,a){let o=e.has("WEBGL_multisampled_render_to_texture")?e.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),l=new ne,h=new WeakMap,u=new Set,d,p=new WeakMap,g=!1;try{g=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function v(C,M){return g?new OffscreenCanvas(C,M):xr("canvas")}function f(C,M,O){let G=1,Y=ht(C);if((Y.width>O||Y.height>O)&&(G=O/Math.max(Y.width,Y.height)),G<1)if(typeof HTMLImageElement<"u"&&C instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&C instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&C instanceof ImageBitmap||typeof VideoFrame<"u"&&C instanceof VideoFrame){let ce=Math.floor(G*Y.width),he=Math.floor(G*Y.height);d===void 0&&(d=v(ce,he));let K=M?v(ce,he):d;return K.width=ce,K.height=he,K.getContext("2d").drawImage(C,0,0,ce,he),Le("WebGLRenderer: Texture has been resized from ("+Y.width+"x"+Y.height+") to ("+ce+"x"+he+")."),K}else return"data"in C&&Le("WebGLRenderer: Image in DataTexture is too big ("+Y.width+"x"+Y.height+")."),C;return C}function m(C){return C.generateMipmaps}function _(C){s.generateMipmap(C)}function b(C){return C.isWebGLCubeRenderTarget?s.TEXTURE_CUBE_MAP:C.isWebGL3DRenderTarget?s.TEXTURE_3D:C.isWebGLArrayRenderTarget||C.isCompressedArrayTexture?s.TEXTURE_2D_ARRAY:s.TEXTURE_2D}function x(C,M,O,G,Y,ce=!1){if(C!==null){if(s[C]!==void 0)return s[C];Le("WebGLRenderer: Attempt to use non-existing WebGL internal format '"+C+"'")}let he;G&&(he=e.get("EXT_texture_norm16"),he||Le("WebGLRenderer: Unable to use normalized textures without EXT_texture_norm16 extension"));let K=M;if(M===s.RED&&(O===s.FLOAT&&(K=s.R32F),O===s.HALF_FLOAT&&(K=s.R16F),O===s.UNSIGNED_BYTE&&(K=s.R8),O===s.UNSIGNED_SHORT&&he&&(K=he.R16_EXT),O===s.SHORT&&he&&(K=he.R16_SNORM_EXT)),M===s.RED_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.R8UI),O===s.UNSIGNED_SHORT&&(K=s.R16UI),O===s.UNSIGNED_INT&&(K=s.R32UI),O===s.BYTE&&(K=s.R8I),O===s.SHORT&&(K=s.R16I),O===s.INT&&(K=s.R32I)),M===s.RG&&(O===s.FLOAT&&(K=s.RG32F),O===s.HALF_FLOAT&&(K=s.RG16F),O===s.UNSIGNED_BYTE&&(K=s.RG8),O===s.UNSIGNED_SHORT&&he&&(K=he.RG16_EXT),O===s.SHORT&&he&&(K=he.RG16_SNORM_EXT)),M===s.RG_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.RG8UI),O===s.UNSIGNED_SHORT&&(K=s.RG16UI),O===s.UNSIGNED_INT&&(K=s.RG32UI),O===s.BYTE&&(K=s.RG8I),O===s.SHORT&&(K=s.RG16I),O===s.INT&&(K=s.RG32I)),M===s.RGB_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.RGB8UI),O===s.UNSIGNED_SHORT&&(K=s.RGB16UI),O===s.UNSIGNED_INT&&(K=s.RGB32UI),O===s.BYTE&&(K=s.RGB8I),O===s.SHORT&&(K=s.RGB16I),O===s.INT&&(K=s.RGB32I)),M===s.RGBA_INTEGER&&(O===s.UNSIGNED_BYTE&&(K=s.RGBA8UI),O===s.UNSIGNED_SHORT&&(K=s.RGBA16UI),O===s.UNSIGNED_INT&&(K=s.RGBA32UI),O===s.BYTE&&(K=s.RGBA8I),O===s.SHORT&&(K=s.RGBA16I),O===s.INT&&(K=s.RGBA32I)),M===s.RGB&&(O===s.UNSIGNED_SHORT&&he&&(K=he.RGB16_EXT),O===s.SHORT&&he&&(K=he.RGB16_SNORM_EXT),O===s.UNSIGNED_INT_5_9_9_9_REV&&(K=s.RGB9_E5),O===s.UNSIGNED_INT_10F_11F_11F_REV&&(K=s.R11F_G11F_B10F)),M===s.RGBA){let $=ce?aa:it.getTransfer(Y);O===s.FLOAT&&(K=s.RGBA32F),O===s.HALF_FLOAT&&(K=s.RGBA16F),O===s.UNSIGNED_BYTE&&(K=$===_t?s.SRGB8_ALPHA8:s.RGBA8),O===s.UNSIGNED_SHORT&&he&&(K=he.RGBA16_EXT),O===s.SHORT&&he&&(K=he.RGBA16_SNORM_EXT),O===s.UNSIGNED_SHORT_4_4_4_4&&(K=s.RGBA4),O===s.UNSIGNED_SHORT_5_5_5_1&&(K=s.RGB5_A1)}return(K===s.R16F||K===s.R32F||K===s.RG16F||K===s.RG32F||K===s.RGBA16F||K===s.RGBA32F)&&e.get("EXT_color_buffer_float"),K}function T(C,M){let O;return C?M===null||M===oi||M===Dr?O=s.DEPTH24_STENCIL8:M===Dn?O=s.DEPTH32F_STENCIL8:M===Nr&&(O=s.DEPTH24_STENCIL8,Le("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):M===null||M===oi||M===Dr?O=s.DEPTH_COMPONENT24:M===Dn?O=s.DEPTH_COMPONENT32F:M===Nr&&(O=s.DEPTH_COMPONENT16),O}function S(C,M){return m(C)===!0||C.isFramebufferTexture&&C.minFilter!==Wt&&C.minFilter!==Xt?Math.log2(Math.max(M.width,M.height))+1:C.mipmaps!==void 0&&C.mipmaps.length>0?C.mipmaps.length:C.isCompressedTexture&&Array.isArray(C.image)?M.mipmaps.length:1}function A(C){let M=C.target;M.removeEventListener("dispose",A),E(M),M.isVideoTexture&&h.delete(M),M.isHTMLTexture&&u.delete(M)}function y(C){let M=C.target;M.removeEventListener("dispose",y),L(M)}function E(C){let M=n.get(C);if(M.__webglInit===void 0)return;let O=C.source,G=p.get(O);if(G){let Y=G[M.__cacheKey];Y.usedTimes--,Y.usedTimes===0&&I(C),Object.keys(G).length===0&&p.delete(O)}n.remove(C)}function I(C){let M=n.get(C);s.deleteTexture(M.__webglTexture);let O=C.source,G=p.get(O);delete G[M.__cacheKey],a.memory.textures--}function L(C){let M=n.get(C);if(C.depthTexture&&(C.depthTexture.dispose(),n.remove(C.depthTexture)),C.isWebGLCubeRenderTarget)for(let G=0;G<6;G++){if(Array.isArray(M.__webglFramebuffer[G]))for(let Y=0;Y<M.__webglFramebuffer[G].length;Y++)s.deleteFramebuffer(M.__webglFramebuffer[G][Y]);else s.deleteFramebuffer(M.__webglFramebuffer[G]);M.__webglDepthbuffer&&s.deleteRenderbuffer(M.__webglDepthbuffer[G])}else{if(Array.isArray(M.__webglFramebuffer))for(let G=0;G<M.__webglFramebuffer.length;G++)s.deleteFramebuffer(M.__webglFramebuffer[G]);else s.deleteFramebuffer(M.__webglFramebuffer);if(M.__webglDepthbuffer&&s.deleteRenderbuffer(M.__webglDepthbuffer),M.__webglMultisampledFramebuffer&&s.deleteFramebuffer(M.__webglMultisampledFramebuffer),M.__webglColorRenderbuffer)for(let G=0;G<M.__webglColorRenderbuffer.length;G++)M.__webglColorRenderbuffer[G]&&s.deleteRenderbuffer(M.__webglColorRenderbuffer[G]);M.__webglDepthRenderbuffer&&s.deleteRenderbuffer(M.__webglDepthRenderbuffer)}let O=C.textures;for(let G=0,Y=O.length;G<Y;G++){let ce=n.get(O[G]);ce.__webglTexture&&(s.deleteTexture(ce.__webglTexture),a.memory.textures--),n.remove(O[G])}n.remove(C)}let F=0;function V(){F=0}function D(){return F}function B(C){F=C}function X(){let C=F;return C>=i.maxTextures&&Le("WebGLTextures: Trying to use "+(C+1)+" texture units while this GPU supports only "+i.maxTextures),F+=1,C}function W(C){let M=[];return M.push(C.wrapS),M.push(C.wrapT),M.push(C.wrapR||0),M.push(C.magFilter),M.push(C.minFilter),M.push(C.anisotropy),M.push(C.internalFormat),M.push(C.format),M.push(C.type),M.push(C.generateMipmaps),M.push(C.premultiplyAlpha),M.push(C.flipY),M.push(C.unpackAlignment),M.push(C.colorSpace),M.join()}function re(C,M){let O=n.get(C);if(C.isVideoTexture&&P(C),C.isRenderTargetTexture===!1&&C.isExternalTexture!==!0&&C.version>0&&O.__version!==C.version){let G=C.image;if(G===null)Le("WebGLRenderer: Texture marked for update but no image data found.");else if(G.complete===!1)Le("WebGLRenderer: Texture marked for update but image is incomplete");else{_e(O,C,M);return}}else C.isExternalTexture&&(O.__webglTexture=C.sourceTexture?C.sourceTexture:null);t.bindTexture(s.TEXTURE_2D,O.__webglTexture,s.TEXTURE0+M)}function q(C,M){let O=n.get(C);if(C.isRenderTargetTexture===!1&&C.version>0&&O.__version!==C.version){_e(O,C,M);return}else C.isExternalTexture&&(O.__webglTexture=C.sourceTexture?C.sourceTexture:null);t.bindTexture(s.TEXTURE_2D_ARRAY,O.__webglTexture,s.TEXTURE0+M)}function j(C,M){let O=n.get(C);if(C.isRenderTargetTexture===!1&&C.version>0&&O.__version!==C.version){_e(O,C,M);return}t.bindTexture(s.TEXTURE_3D,O.__webglTexture,s.TEXTURE0+M)}function te(C,M){let O=n.get(C);if(C.isCubeDepthTexture!==!0&&C.version>0&&O.__version!==C.version){We(O,C,M);return}t.bindTexture(s.TEXTURE_CUBE_MAP,O.__webglTexture,s.TEXTURE0+M)}let Ne={[_i]:s.REPEAT,[rn]:s.CLAMP_TO_EDGE,[mr]:s.MIRRORED_REPEAT},Ae={[Wt]:s.NEAREST,[bl]:s.NEAREST_MIPMAP_NEAREST,[Bs]:s.NEAREST_MIPMAP_LINEAR,[Xt]:s.LINEAR,[Lr]:s.LINEAR_MIPMAP_NEAREST,[ai]:s.LINEAR_MIPMAP_LINEAR},vt={[Hf]:s.NEVER,[Kf]:s.ALWAYS,[Wf]:s.LESS,[lc]:s.LEQUAL,[Xf]:s.EQUAL,[cc]:s.GEQUAL,[qf]:s.GREATER,[Yf]:s.NOTEQUAL};function ct(C,M){if(M.type===Dn&&e.has("OES_texture_float_linear")===!1&&(M.magFilter===Xt||M.magFilter===Lr||M.magFilter===Bs||M.magFilter===ai||M.minFilter===Xt||M.minFilter===Lr||M.minFilter===Bs||M.minFilter===ai)&&Le("WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),s.texParameteri(C,s.TEXTURE_WRAP_S,Ne[M.wrapS]),s.texParameteri(C,s.TEXTURE_WRAP_T,Ne[M.wrapT]),(C===s.TEXTURE_3D||C===s.TEXTURE_2D_ARRAY)&&s.texParameteri(C,s.TEXTURE_WRAP_R,Ne[M.wrapR]),s.texParameteri(C,s.TEXTURE_MAG_FILTER,Ae[M.magFilter]),s.texParameteri(C,s.TEXTURE_MIN_FILTER,Ae[M.minFilter]),M.compareFunction&&(s.texParameteri(C,s.TEXTURE_COMPARE_MODE,s.COMPARE_REF_TO_TEXTURE),s.texParameteri(C,s.TEXTURE_COMPARE_FUNC,vt[M.compareFunction])),e.has("EXT_texture_filter_anisotropic")===!0){if(M.magFilter===Wt||M.minFilter!==Bs&&M.minFilter!==ai||M.type===Dn&&e.has("OES_texture_float_linear")===!1)return;if(M.anisotropy>1||n.get(M).__currentAnisotropy){let O=e.get("EXT_texture_filter_anisotropic");s.texParameterf(C,O.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(M.anisotropy,i.getMaxAnisotropy())),n.get(M).__currentAnisotropy=M.anisotropy}}}function mt(C,M){let O=!1;C.__webglInit===void 0&&(C.__webglInit=!0,M.addEventListener("dispose",A));let G=M.source,Y=p.get(G);Y===void 0&&(Y={},p.set(G,Y));let ce=W(M);if(ce!==C.__cacheKey){Y[ce]===void 0&&(Y[ce]={texture:s.createTexture(),usedTimes:0},a.memory.textures++,O=!0),Y[ce].usedTimes++;let he=Y[C.__cacheKey];he!==void 0&&(Y[C.__cacheKey].usedTimes--,he.usedTimes===0&&I(M)),C.__cacheKey=ce,C.__webglTexture=Y[ce].texture}return O}function Z(C,M,O){return Math.floor(Math.floor(C/O)/M)}function Q(C,M,O,G){let ce=C.updateRanges;if(ce.length===0)t.texSubImage2D(s.TEXTURE_2D,0,0,0,M.width,M.height,O,G,M.data);else{ce.sort((De,ge)=>De.start-ge.start);let he=0;for(let De=1;De<ce.length;De++){let ge=ce[he],fe=ce[De],Ue=ge.start+ge.count,Ge=Z(fe.start,M.width,4),et=Z(ge.start,M.width,4);fe.start<=Ue+1&&Ge===et&&Z(fe.start+fe.count-1,M.width,4)===Ge?ge.count=Math.max(ge.count,fe.start+fe.count-ge.start):(++he,ce[he]=fe)}ce.length=he+1;let K=t.getParameter(s.UNPACK_ROW_LENGTH),$=t.getParameter(s.UNPACK_SKIP_PIXELS),de=t.getParameter(s.UNPACK_SKIP_ROWS);t.pixelStorei(s.UNPACK_ROW_LENGTH,M.width);for(let De=0,ge=ce.length;De<ge;De++){let fe=ce[De],Ue=Math.floor(fe.start/4),Ge=Math.ceil(fe.count/4),et=Ue%M.width,U=Math.floor(Ue/M.width),pe=Ge,J=1;t.pixelStorei(s.UNPACK_SKIP_PIXELS,et),t.pixelStorei(s.UNPACK_SKIP_ROWS,U),t.texSubImage2D(s.TEXTURE_2D,0,et,U,pe,J,O,G,M.data)}C.clearUpdateRanges(),t.pixelStorei(s.UNPACK_ROW_LENGTH,K),t.pixelStorei(s.UNPACK_SKIP_PIXELS,$),t.pixelStorei(s.UNPACK_SKIP_ROWS,de)}}function _e(C,M,O){let G=s.TEXTURE_2D;(M.isDataArrayTexture||M.isCompressedArrayTexture)&&(G=s.TEXTURE_2D_ARRAY),M.isData3DTexture&&(G=s.TEXTURE_3D);let Y=mt(C,M),ce=M.source;t.bindTexture(G,C.__webglTexture,s.TEXTURE0+O);let he=n.get(ce);if(ce.version!==he.__version||Y===!0){if(t.activeTexture(s.TEXTURE0+O),(typeof ImageBitmap<"u"&&M.image instanceof ImageBitmap)===!1){let J=it.getPrimaries(it.workingColorSpace),me=M.colorSpace===Xi?null:it.getPrimaries(M.colorSpace),Se=M.colorSpace===Xi||J===me?s.NONE:s.BROWSER_DEFAULT_WEBGL;t.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,M.flipY),t.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,M.premultiplyAlpha),t.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,Se)}t.pixelStorei(s.UNPACK_ALIGNMENT,M.unpackAlignment);let $=f(M.image,!1,i.maxTextureSize);$=Mt(M,$);let de=r.convert(M.format,M.colorSpace),De=r.convert(M.type),ge=x(M.internalFormat,de,De,M.normalized,M.colorSpace,M.isVideoTexture);ct(G,M);let fe,Ue=M.mipmaps,Ge=M.isVideoTexture!==!0,et=he.__version===void 0||Y===!0,U=ce.dataReady,pe=S(M,$);if(M.isDepthTexture)ge=T(M.format===ds,M.type),et&&(Ge?t.texStorage2D(s.TEXTURE_2D,1,ge,$.width,$.height):t.texImage2D(s.TEXTURE_2D,0,ge,$.width,$.height,0,de,De,null));else if(M.isDataTexture)if(Ue.length>0){Ge&&et&&t.texStorage2D(s.TEXTURE_2D,pe,ge,Ue[0].width,Ue[0].height);for(let J=0,me=Ue.length;J<me;J++)fe=Ue[J],Ge?U&&t.texSubImage2D(s.TEXTURE_2D,J,0,0,fe.width,fe.height,de,De,fe.data):t.texImage2D(s.TEXTURE_2D,J,ge,fe.width,fe.height,0,de,De,fe.data);M.generateMipmaps=!1}else Ge?(et&&t.texStorage2D(s.TEXTURE_2D,pe,ge,$.width,$.height),U&&Q(M,$,de,De)):t.texImage2D(s.TEXTURE_2D,0,ge,$.width,$.height,0,de,De,$.data);else if(M.isCompressedTexture)if(M.isCompressedArrayTexture){Ge&&et&&t.texStorage3D(s.TEXTURE_2D_ARRAY,pe,ge,Ue[0].width,Ue[0].height,$.depth);for(let J=0,me=Ue.length;J<me;J++)if(fe=Ue[J],M.format!==Un)if(de!==null)if(Ge){if(U)if(M.layerUpdates.size>0){let Se=au(fe.width,fe.height,M.format,M.type);for(let ie of M.layerUpdates){let Fe=fe.data.subarray(ie*Se/fe.data.BYTES_PER_ELEMENT,(ie+1)*Se/fe.data.BYTES_PER_ELEMENT);t.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,J,0,0,ie,fe.width,fe.height,1,de,Fe)}}else t.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,J,0,0,0,fe.width,fe.height,$.depth,de,fe.data)}else t.compressedTexImage3D(s.TEXTURE_2D_ARRAY,J,ge,fe.width,fe.height,$.depth,0,fe.data,0,0);else Le("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else Ge?U&&t.texSubImage3D(s.TEXTURE_2D_ARRAY,J,0,0,0,fe.width,fe.height,$.depth,de,De,fe.data):t.texImage3D(s.TEXTURE_2D_ARRAY,J,ge,fe.width,fe.height,$.depth,0,de,De,fe.data);M.layerUpdates.size>0&&M.clearLayerUpdates()}else{Ge&&et&&t.texStorage2D(s.TEXTURE_2D,pe,ge,Ue[0].width,Ue[0].height);for(let J=0,me=Ue.length;J<me;J++)fe=Ue[J],M.format!==Un?de!==null?Ge?U&&t.compressedTexSubImage2D(s.TEXTURE_2D,J,0,0,fe.width,fe.height,de,fe.data):t.compressedTexImage2D(s.TEXTURE_2D,J,ge,fe.width,fe.height,0,fe.data):Le("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):Ge?U&&t.texSubImage2D(s.TEXTURE_2D,J,0,0,fe.width,fe.height,de,De,fe.data):t.texImage2D(s.TEXTURE_2D,J,ge,fe.width,fe.height,0,de,De,fe.data)}else if(M.isDataArrayTexture)if(Ge){if(et&&t.texStorage3D(s.TEXTURE_2D_ARRAY,pe,ge,$.width,$.height,$.depth),U)if(M.layerUpdates.size>0){let J=au($.width,$.height,M.format,M.type);for(let me of M.layerUpdates){let Se=$.data.subarray(me*J/$.data.BYTES_PER_ELEMENT,(me+1)*J/$.data.BYTES_PER_ELEMENT);t.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,me,$.width,$.height,1,de,De,Se)}M.clearLayerUpdates()}else t.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,0,$.width,$.height,$.depth,de,De,$.data)}else t.texImage3D(s.TEXTURE_2D_ARRAY,0,ge,$.width,$.height,$.depth,0,de,De,$.data);else if(M.isData3DTexture)Ge?(et&&t.texStorage3D(s.TEXTURE_3D,pe,ge,$.width,$.height,$.depth),U&&t.texSubImage3D(s.TEXTURE_3D,0,0,0,0,$.width,$.height,$.depth,de,De,$.data)):t.texImage3D(s.TEXTURE_3D,0,ge,$.width,$.height,$.depth,0,de,De,$.data);else if(M.isFramebufferTexture){if(et)if(Ge)t.texStorage2D(s.TEXTURE_2D,pe,ge,$.width,$.height);else{let J=$.width,me=$.height;for(let Se=0;Se<pe;Se++)t.texImage2D(s.TEXTURE_2D,Se,ge,J,me,0,de,De,null),J>>=1,me>>=1}}else if(M.isHTMLTexture){if("texElementImage2D"in s){let J=s.canvas;if(J.hasAttribute("layoutsubtree")||J.setAttribute("layoutsubtree","true"),$.parentNode!==J){J.appendChild($),u.add(M),J.onpaint=me=>{let Se=me.changedElements;for(let ie of u)Se.includes(ie.image)&&(ie.needsUpdate=!0)},J.requestPaint();return}if(s.texElementImage2D.length===3)s.texElementImage2D(s.TEXTURE_2D,s.RGBA8,$);else{let Se=s.RGBA,ie=s.RGBA,Fe=s.UNSIGNED_BYTE;s.texElementImage2D(s.TEXTURE_2D,0,Se,ie,Fe,$)}s.texParameteri(s.TEXTURE_2D,s.TEXTURE_MIN_FILTER,s.LINEAR),s.texParameteri(s.TEXTURE_2D,s.TEXTURE_WRAP_S,s.CLAMP_TO_EDGE),s.texParameteri(s.TEXTURE_2D,s.TEXTURE_WRAP_T,s.CLAMP_TO_EDGE)}}else if(Ue.length>0){if(Ge&&et){let J=ht(Ue[0]);t.texStorage2D(s.TEXTURE_2D,pe,ge,J.width,J.height)}for(let J=0,me=Ue.length;J<me;J++)fe=Ue[J],Ge?U&&t.texSubImage2D(s.TEXTURE_2D,J,0,0,de,De,fe):t.texImage2D(s.TEXTURE_2D,J,ge,de,De,fe);M.generateMipmaps=!1}else if(Ge){if(et){let J=ht($);t.texStorage2D(s.TEXTURE_2D,pe,ge,J.width,J.height)}U&&t.texSubImage2D(s.TEXTURE_2D,0,0,0,de,De,$)}else t.texImage2D(s.TEXTURE_2D,0,ge,de,De,$);m(M)&&_(G),he.__version=ce.version,M.onUpdate&&M.onUpdate(M)}C.__version=M.version}function We(C,M,O){if(M.image.length!==6)return;let G=mt(C,M),Y=M.source;t.bindTexture(s.TEXTURE_CUBE_MAP,C.__webglTexture,s.TEXTURE0+O);let ce=n.get(Y);if(Y.version!==ce.__version||G===!0){t.activeTexture(s.TEXTURE0+O);let he=it.getPrimaries(it.workingColorSpace),K=M.colorSpace===Xi?null:it.getPrimaries(M.colorSpace),$=M.colorSpace===Xi||he===K?s.NONE:s.BROWSER_DEFAULT_WEBGL;t.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,M.flipY),t.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,M.premultiplyAlpha),t.pixelStorei(s.UNPACK_ALIGNMENT,M.unpackAlignment),t.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,$);let de=M.isCompressedTexture||M.image[0].isCompressedTexture,De=M.image[0]&&M.image[0].isDataTexture,ge=[];for(let ie=0;ie<6;ie++)!de&&!De?ge[ie]=f(M.image[ie],!0,i.maxCubemapSize):ge[ie]=De?M.image[ie].image:M.image[ie],ge[ie]=Mt(M,ge[ie]);let fe=ge[0],Ue=r.convert(M.format,M.colorSpace),Ge=r.convert(M.type),et=x(M.internalFormat,Ue,Ge,M.normalized,M.colorSpace),U=M.isVideoTexture!==!0,pe=ce.__version===void 0||G===!0,J=Y.dataReady,me=S(M,fe);ct(s.TEXTURE_CUBE_MAP,M);let Se;if(de){U&&pe&&t.texStorage2D(s.TEXTURE_CUBE_MAP,me,et,fe.width,fe.height);for(let ie=0;ie<6;ie++){Se=ge[ie].mipmaps;for(let Fe=0;Fe<Se.length;Fe++){let Ie=Se[Fe];M.format!==Un?Ue!==null?U?J&&t.compressedTexSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe,0,0,Ie.width,Ie.height,Ue,Ie.data):t.compressedTexImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe,et,Ie.width,Ie.height,0,Ie.data):Le("WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):U?J&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe,0,0,Ie.width,Ie.height,Ue,Ge,Ie.data):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe,et,Ie.width,Ie.height,0,Ue,Ge,Ie.data)}}}else{if(Se=M.mipmaps,U&&pe){Se.length>0&&me++;let ie=ht(ge[0]);t.texStorage2D(s.TEXTURE_CUBE_MAP,me,et,ie.width,ie.height)}for(let ie=0;ie<6;ie++)if(De){U?J&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,0,0,0,ge[ie].width,ge[ie].height,Ue,Ge,ge[ie].data):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,0,et,ge[ie].width,ge[ie].height,0,Ue,Ge,ge[ie].data);for(let Fe=0;Fe<Se.length;Fe++){let Dt=Se[Fe].image[ie].image;U?J&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe+1,0,0,Dt.width,Dt.height,Ue,Ge,Dt.data):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe+1,et,Dt.width,Dt.height,0,Ue,Ge,Dt.data)}}else{U?J&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,0,0,0,Ue,Ge,ge[ie]):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,0,et,Ue,Ge,ge[ie]);for(let Fe=0;Fe<Se.length;Fe++){let Ie=Se[Fe];U?J&&t.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe+1,0,0,Ue,Ge,Ie.image[ie]):t.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ie,Fe+1,et,Ue,Ge,Ie.image[ie])}}}m(M)&&_(s.TEXTURE_CUBE_MAP),ce.__version=Y.version,M.onUpdate&&M.onUpdate(M)}C.__version=M.version}function be(C,M,O,G,Y,ce){let he=r.convert(O.format,O.colorSpace),K=r.convert(O.type),$=x(O.internalFormat,he,K,O.normalized,O.colorSpace),de=n.get(M),De=n.get(O);if(De.__renderTarget=M,!de.__hasExternalTextures){let ge=Math.max(1,M.width>>ce),fe=Math.max(1,M.height>>ce);Y===s.TEXTURE_3D||Y===s.TEXTURE_2D_ARRAY?t.texImage3D(Y,ce,$,ge,fe,M.depth,0,he,K,null):t.texImage2D(Y,ce,$,ge,fe,0,he,K,null)}t.bindFramebuffer(s.FRAMEBUFFER,C),$e(M)?o.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,G,Y,De.__webglTexture,0,qe(M)):(Y===s.TEXTURE_2D||Y>=s.TEXTURE_CUBE_MAP_POSITIVE_X&&Y<=s.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&s.framebufferTexture2D(s.FRAMEBUFFER,G,Y,De.__webglTexture,ce),t.bindFramebuffer(s.FRAMEBUFFER,null)}function Xe(C,M,O){if(s.bindRenderbuffer(s.RENDERBUFFER,C),M.depthBuffer){let G=M.depthTexture,Y=G&&G.isDepthTexture?G.type:null,ce=T(M.stencilBuffer,Y),he=M.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;$e(M)?o.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,qe(M),ce,M.width,M.height):O?s.renderbufferStorageMultisample(s.RENDERBUFFER,qe(M),ce,M.width,M.height):s.renderbufferStorage(s.RENDERBUFFER,ce,M.width,M.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,he,s.RENDERBUFFER,C)}else{let G=M.textures;for(let Y=0;Y<G.length;Y++){let ce=G[Y],he=r.convert(ce.format,ce.colorSpace),K=r.convert(ce.type),$=x(ce.internalFormat,he,K,ce.normalized,ce.colorSpace);$e(M)?o.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,qe(M),$,M.width,M.height):O?s.renderbufferStorageMultisample(s.RENDERBUFFER,qe(M),$,M.width,M.height):s.renderbufferStorage(s.RENDERBUFFER,$,M.width,M.height)}}s.bindRenderbuffer(s.RENDERBUFFER,null)}function Tt(C,M,O){let G=M.isWebGLCubeRenderTarget===!0;if(t.bindFramebuffer(s.FRAMEBUFFER,C),!(M.depthTexture&&M.depthTexture.isDepthTexture))throw new Error("THREE.WebGLTextures: renderTarget.depthTexture must be an instance of THREE.DepthTexture.");let Y=n.get(M.depthTexture);if(Y.__renderTarget=M,(!Y.__webglTexture||M.depthTexture.image.width!==M.width||M.depthTexture.image.height!==M.height)&&(M.depthTexture.image.width=M.width,M.depthTexture.image.height=M.height,M.depthTexture.needsUpdate=!0),G){if(Y.__webglInit===void 0&&(Y.__webglInit=!0,M.depthTexture.addEventListener("dispose",A)),Y.__webglTexture===void 0){Y.__webglTexture=s.createTexture(),t.bindTexture(s.TEXTURE_CUBE_MAP,Y.__webglTexture),ct(s.TEXTURE_CUBE_MAP,M.depthTexture);let de=r.convert(M.depthTexture.format),De=r.convert(M.depthTexture.type),ge;M.depthTexture.format===yi?ge=s.DEPTH_COMPONENT24:M.depthTexture.format===ds&&(ge=s.DEPTH24_STENCIL8);for(let fe=0;fe<6;fe++)s.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+fe,0,ge,M.width,M.height,0,de,De,null)}}else re(M.depthTexture,0);let ce=Y.__webglTexture,he=qe(M),K=G?s.TEXTURE_CUBE_MAP_POSITIVE_X+O:s.TEXTURE_2D,$=M.depthTexture.format===ds?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;if(M.depthTexture.format===yi)$e(M)?o.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,$,K,ce,0,he):s.framebufferTexture2D(s.FRAMEBUFFER,$,K,ce,0);else if(M.depthTexture.format===ds)$e(M)?o.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,$,K,ce,0,he):s.framebufferTexture2D(s.FRAMEBUFFER,$,K,ce,0);else throw new Error("THREE.WebGLTextures: Unknown depthTexture format.")}function ee(C){let M=n.get(C),O=C.isWebGLCubeRenderTarget===!0;if(M.__boundDepthTexture!==C.depthTexture){let G=C.depthTexture;if(M.__depthDisposeCallback&&M.__depthDisposeCallback(),G){let Y=()=>{delete M.__boundDepthTexture,delete M.__depthDisposeCallback,G.removeEventListener("dispose",Y)};G.addEventListener("dispose",Y),M.__depthDisposeCallback=Y}M.__boundDepthTexture=G}if(C.depthTexture&&!M.__autoAllocateDepthBuffer)if(O)for(let G=0;G<6;G++)Tt(M.__webglFramebuffer[G],C,G);else{let G=C.texture.mipmaps;G&&G.length>0?Tt(M.__webglFramebuffer[0],C,0):Tt(M.__webglFramebuffer,C,0)}else if(O){M.__webglDepthbuffer=[];for(let G=0;G<6;G++)if(t.bindFramebuffer(s.FRAMEBUFFER,M.__webglFramebuffer[G]),M.__webglDepthbuffer[G]===void 0)M.__webglDepthbuffer[G]=s.createRenderbuffer(),Xe(M.__webglDepthbuffer[G],C,!1);else{let Y=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,ce=M.__webglDepthbuffer[G];s.bindRenderbuffer(s.RENDERBUFFER,ce),s.framebufferRenderbuffer(s.FRAMEBUFFER,Y,s.RENDERBUFFER,ce)}}else{let G=C.texture.mipmaps;if(G&&G.length>0?t.bindFramebuffer(s.FRAMEBUFFER,M.__webglFramebuffer[0]):t.bindFramebuffer(s.FRAMEBUFFER,M.__webglFramebuffer),M.__webglDepthbuffer===void 0)M.__webglDepthbuffer=s.createRenderbuffer(),Xe(M.__webglDepthbuffer,C,!1);else{let Y=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,ce=M.__webglDepthbuffer;s.bindRenderbuffer(s.RENDERBUFFER,ce),s.framebufferRenderbuffer(s.FRAMEBUFFER,Y,s.RENDERBUFFER,ce)}}t.bindFramebuffer(s.FRAMEBUFFER,null)}function ae(C,M,O){let G=n.get(C);M!==void 0&&be(G.__webglFramebuffer,C,C.texture,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,0),O!==void 0&&ee(C)}function oe(C){let M=C.texture,O=n.get(C),G=n.get(M);C.addEventListener("dispose",y);let Y=C.textures,ce=C.isWebGLCubeRenderTarget===!0,he=Y.length>1;if(he||(G.__webglTexture===void 0&&(G.__webglTexture=s.createTexture()),G.__version=M.version,a.memory.textures++),ce){O.__webglFramebuffer=[];for(let K=0;K<6;K++)if(M.mipmaps&&M.mipmaps.length>0){O.__webglFramebuffer[K]=[];for(let $=0;$<M.mipmaps.length;$++)O.__webglFramebuffer[K][$]=s.createFramebuffer()}else O.__webglFramebuffer[K]=s.createFramebuffer()}else{if(M.mipmaps&&M.mipmaps.length>0){O.__webglFramebuffer=[];for(let K=0;K<M.mipmaps.length;K++)O.__webglFramebuffer[K]=s.createFramebuffer()}else O.__webglFramebuffer=s.createFramebuffer();if(he)for(let K=0,$=Y.length;K<$;K++){let de=n.get(Y[K]);de.__webglTexture===void 0&&(de.__webglTexture=s.createTexture(),a.memory.textures++)}if(C.samples>0&&$e(C)===!1){O.__webglMultisampledFramebuffer=s.createFramebuffer(),O.__webglColorRenderbuffer=[],t.bindFramebuffer(s.FRAMEBUFFER,O.__webglMultisampledFramebuffer);for(let K=0;K<Y.length;K++){let $=Y[K];O.__webglColorRenderbuffer[K]=s.createRenderbuffer(),s.bindRenderbuffer(s.RENDERBUFFER,O.__webglColorRenderbuffer[K]);let de=r.convert($.format,$.colorSpace),De=r.convert($.type),ge=x($.internalFormat,de,De,$.normalized,$.colorSpace,C.isXRRenderTarget===!0),fe=qe(C);s.renderbufferStorageMultisample(s.RENDERBUFFER,fe,ge,C.width,C.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+K,s.RENDERBUFFER,O.__webglColorRenderbuffer[K])}s.bindRenderbuffer(s.RENDERBUFFER,null),C.depthBuffer&&(O.__webglDepthRenderbuffer=s.createRenderbuffer(),Xe(O.__webglDepthRenderbuffer,C,!0)),t.bindFramebuffer(s.FRAMEBUFFER,null)}}if(ce){t.bindTexture(s.TEXTURE_CUBE_MAP,G.__webglTexture),ct(s.TEXTURE_CUBE_MAP,M);for(let K=0;K<6;K++)if(M.mipmaps&&M.mipmaps.length>0)for(let $=0;$<M.mipmaps.length;$++)be(O.__webglFramebuffer[K][$],C,M,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+K,$);else be(O.__webglFramebuffer[K],C,M,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+K,0);m(M)&&_(s.TEXTURE_CUBE_MAP),t.unbindTexture()}else if(he){for(let K=0,$=Y.length;K<$;K++){let de=Y[K],De=n.get(de),ge=s.TEXTURE_2D;(C.isWebGL3DRenderTarget||C.isWebGLArrayRenderTarget)&&(ge=C.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),t.bindTexture(ge,De.__webglTexture),ct(ge,de),be(O.__webglFramebuffer,C,de,s.COLOR_ATTACHMENT0+K,ge,0),m(de)&&_(ge)}t.unbindTexture()}else{let K=s.TEXTURE_2D;if((C.isWebGL3DRenderTarget||C.isWebGLArrayRenderTarget)&&(K=C.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),t.bindTexture(K,G.__webglTexture),ct(K,M),M.mipmaps&&M.mipmaps.length>0)for(let $=0;$<M.mipmaps.length;$++)be(O.__webglFramebuffer[$],C,M,s.COLOR_ATTACHMENT0,K,$);else be(O.__webglFramebuffer,C,M,s.COLOR_ATTACHMENT0,K,0);m(M)&&_(K),t.unbindTexture()}C.depthBuffer&&ee(C)}function le(C){let M=C.textures;for(let O=0,G=M.length;O<G;O++){let Y=M[O];if(m(Y)){let ce=b(C),he=n.get(Y).__webglTexture;t.bindTexture(ce,he),_(ce),t.unbindTexture()}}}let ue=[],ze=[];function Be(C){if(C.samples>0){if($e(C)===!1){let M=C.textures,O=C.width,G=C.height,Y=s.COLOR_BUFFER_BIT,ce=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,he=n.get(C),K=M.length>1;if(K)for(let de=0;de<M.length;de++)t.bindFramebuffer(s.FRAMEBUFFER,he.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+de,s.RENDERBUFFER,null),t.bindFramebuffer(s.FRAMEBUFFER,he.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+de,s.TEXTURE_2D,null,0);t.bindFramebuffer(s.READ_FRAMEBUFFER,he.__webglMultisampledFramebuffer);let $=C.texture.mipmaps;$&&$.length>0?t.bindFramebuffer(s.DRAW_FRAMEBUFFER,he.__webglFramebuffer[0]):t.bindFramebuffer(s.DRAW_FRAMEBUFFER,he.__webglFramebuffer);for(let de=0;de<M.length;de++){if(C.resolveDepthBuffer&&(C.depthBuffer&&(Y|=s.DEPTH_BUFFER_BIT),C.stencilBuffer&&C.resolveStencilBuffer&&(Y|=s.STENCIL_BUFFER_BIT)),K){s.framebufferRenderbuffer(s.READ_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.RENDERBUFFER,he.__webglColorRenderbuffer[de]);let De=n.get(M[de]).__webglTexture;s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,De,0)}s.blitFramebuffer(0,0,O,G,0,0,O,G,Y,s.NEAREST),c===!0&&(ue.length=0,ze.length=0,ue.push(s.COLOR_ATTACHMENT0+de),C.depthBuffer&&C.storeMultisampledDepthBuffer===!1&&(ue.push(ce),ze.push(ce),s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,ze)),s.invalidateFramebuffer(s.READ_FRAMEBUFFER,ue))}if(t.bindFramebuffer(s.READ_FRAMEBUFFER,null),t.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),K)for(let de=0;de<M.length;de++){t.bindFramebuffer(s.FRAMEBUFFER,he.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+de,s.RENDERBUFFER,he.__webglColorRenderbuffer[de]);let De=n.get(M[de]).__webglTexture;t.bindFramebuffer(s.FRAMEBUFFER,he.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+de,s.TEXTURE_2D,De,0)}t.bindFramebuffer(s.DRAW_FRAMEBUFFER,he.__webglMultisampledFramebuffer)}else if(C.depthBuffer&&C.storeMultisampledDepthBuffer===!1&&c){let M=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,[M])}}}function qe(C){return Math.min(i.maxSamples,C.samples)}function $e(C){let M=n.get(C);return C.samples>0&&e.has("WEBGL_multisampled_render_to_texture")===!0&&M.__useRenderToTexture!==!1}function P(C){let M=a.render.frame;h.get(C)!==M&&(h.set(C,M),C.update())}function Mt(C,M){let O=C.colorSpace,G=C.format,Y=C.type;return C.isCompressedTexture===!0||C.isVideoTexture===!0||O!==gn&&O!==Xi&&(it.getTransfer(O)===_t?(G!==Un||Y!==bn)&&Le("WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):He("WebGLTextures: Unsupported texture color space:",O)),M}function ht(C){return typeof HTMLImageElement<"u"&&C instanceof HTMLImageElement?(l.width=C.naturalWidth||C.width,l.height=C.naturalHeight||C.height):typeof VideoFrame<"u"&&C instanceof VideoFrame?(l.width=C.displayWidth,l.height=C.displayHeight):(l.width=C.width,l.height=C.height),l}this.allocateTextureUnit=X,this.resetTextureUnits=V,this.getTextureUnits=D,this.setTextureUnits=B,this.setTexture2D=re,this.setTexture2DArray=q,this.setTexture3D=j,this.setTextureCube=te,this.rebindTextures=ae,this.setupRenderTarget=oe,this.updateRenderTargetMipmap=le,this.updateMultisampleRenderTarget=Be,this.setupDepthRenderbuffer=ee,this.setupFrameBufferTexture=be,this.useMultisampledRTT=$e,this.isReversedDepthBuffer=function(){return t.buffers.depth.getReversed()}}function qv(s,e){function t(n,i=Xi){let r,a=it.getTransfer(i);if(n===bn)return s.UNSIGNED_BYTE;if(n===wl)return s.UNSIGNED_SHORT_4_4_4_4;if(n===Al)return s.UNSIGNED_SHORT_5_5_5_1;if(n===Yh)return s.UNSIGNED_INT_5_9_9_9_REV;if(n===Kh)return s.UNSIGNED_INT_10F_11F_11F_REV;if(n===Xh)return s.BYTE;if(n===qh)return s.SHORT;if(n===Nr)return s.UNSIGNED_SHORT;if(n===Tl)return s.INT;if(n===oi)return s.UNSIGNED_INT;if(n===Dn)return s.FLOAT;if(n===an)return s.HALF_FLOAT;if(n===Zh)return s.ALPHA;if(n===Jh)return s.RGB;if(n===Un)return s.RGBA;if(n===yi)return s.DEPTH_COMPONENT;if(n===ds)return s.DEPTH_STENCIL;if(n===El)return s.RED;if(n===Cl)return s.RED_INTEGER;if(n===fs)return s.RG;if(n===Rl)return s.RG_INTEGER;if(n===Il)return s.RGBA_INTEGER;if(n===Wa||n===Xa||n===qa||n===Ya)if(a===_t)if(r=e.get("WEBGL_compressed_texture_s3tc_srgb"),r!==null){if(n===Wa)return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(n===Xa)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(n===qa)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(n===Ya)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(r=e.get("WEBGL_compressed_texture_s3tc"),r!==null){if(n===Wa)return r.COMPRESSED_RGB_S3TC_DXT1_EXT;if(n===Xa)return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(n===qa)return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(n===Ya)return r.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(n===Pl||n===Ll||n===Nl||n===Dl)if(r=e.get("WEBGL_compressed_texture_pvrtc"),r!==null){if(n===Pl)return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(n===Ll)return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(n===Nl)return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(n===Dl)return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(n===Ul||n===Fl||n===Ol||n===Bl||n===kl||n===Ka||n===zl)if(r=e.get("WEBGL_compressed_texture_etc"),r!==null){if(n===Ul||n===Fl)return a===_t?r.COMPRESSED_SRGB8_ETC2:r.COMPRESSED_RGB8_ETC2;if(n===Ol)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:r.COMPRESSED_RGBA8_ETC2_EAC;if(n===Bl)return r.COMPRESSED_R11_EAC;if(n===kl)return r.COMPRESSED_SIGNED_R11_EAC;if(n===Ka)return r.COMPRESSED_RG11_EAC;if(n===zl)return r.COMPRESSED_SIGNED_RG11_EAC}else return null;if(n===Gl||n===Vl||n===Hl||n===Wl||n===Xl||n===ql||n===Yl||n===Kl||n===Zl||n===Jl||n===$l||n===jl||n===Ql||n===ec)if(r=e.get("WEBGL_compressed_texture_astc"),r!==null){if(n===Gl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:r.COMPRESSED_RGBA_ASTC_4x4_KHR;if(n===Vl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:r.COMPRESSED_RGBA_ASTC_5x4_KHR;if(n===Hl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:r.COMPRESSED_RGBA_ASTC_5x5_KHR;if(n===Wl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:r.COMPRESSED_RGBA_ASTC_6x5_KHR;if(n===Xl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:r.COMPRESSED_RGBA_ASTC_6x6_KHR;if(n===ql)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:r.COMPRESSED_RGBA_ASTC_8x5_KHR;if(n===Yl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:r.COMPRESSED_RGBA_ASTC_8x6_KHR;if(n===Kl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:r.COMPRESSED_RGBA_ASTC_8x8_KHR;if(n===Zl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:r.COMPRESSED_RGBA_ASTC_10x5_KHR;if(n===Jl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:r.COMPRESSED_RGBA_ASTC_10x6_KHR;if(n===$l)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:r.COMPRESSED_RGBA_ASTC_10x8_KHR;if(n===jl)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:r.COMPRESSED_RGBA_ASTC_10x10_KHR;if(n===Ql)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:r.COMPRESSED_RGBA_ASTC_12x10_KHR;if(n===ec)return a===_t?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:r.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(n===tc||n===nc||n===ic)if(r=e.get("EXT_texture_compression_bptc"),r!==null){if(n===tc)return a===_t?r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:r.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(n===nc)return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(n===ic)return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(n===sc||n===rc||n===Za||n===ac)if(r=e.get("EXT_texture_compression_rgtc"),r!==null){if(n===sc)return r.COMPRESSED_RED_RGTC1_EXT;if(n===rc)return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(n===Za)return r.COMPRESSED_RED_GREEN_RGTC2_EXT;if(n===ac)return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return n===Dr?s.UNSIGNED_INT_24_8:s[n]!==void 0?s[n]:null}return{convert:t}}var Yv=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,Kv=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`,vu=class{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(e,t){if(this.texture===null){let n=new xa(e.texture);(e.depthNear!==t.depthNear||e.depthFar!==t.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=n}}getMesh(e){if(this.texture!==null&&this.mesh===null){let t=e.cameras[0].viewport,n=new Bt({vertexShader:Yv,fragmentShader:Kv,uniforms:{depthColor:{value:this.texture},depthWidth:{value:t.z},depthHeight:{value:t.w}}});this.mesh=new Ee(new Rt(20,20),n)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}},Mu=class extends vi{constructor(e,t){super();let n=this,i=null,r=1,a=null,o="local-floor",c=1,l=null,h=null,u=null,d=null,p=null,g=null,v=typeof XRWebGLBinding<"u",f=new vu,m={},_=t.getContextAttributes(),b=null,x=null,T=[],S=[],A=new ne,y=null,E=null,I=new zt;I.viewport=new At;let L=new zt;L.viewport=new At;let F=[I,L],V=new Ml,D=null,B=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(Z){let Q=T[Z];return Q===void 0&&(Q=new vr,T[Z]=Q),Q.getTargetRaySpace()},this.getControllerGrip=function(Z){let Q=T[Z];return Q===void 0&&(Q=new vr,T[Z]=Q),Q.getGripSpace()},this.getHand=function(Z){let Q=T[Z];return Q===void 0&&(Q=new vr,T[Z]=Q),Q.getHandSpace()};function X(Z){let Q=S.indexOf(Z.inputSource);if(Q===-1)return;let _e=T[Q];_e!==void 0&&(_e.update(Z.inputSource,Z.frame,l||a),_e.dispatchEvent({type:Z.type,data:Z.inputSource}))}function W(){i.removeEventListener("select",X),i.removeEventListener("selectstart",X),i.removeEventListener("selectend",X),i.removeEventListener("squeeze",X),i.removeEventListener("squeezestart",X),i.removeEventListener("squeezeend",X),i.removeEventListener("end",W),i.removeEventListener("inputsourceschange",re);for(let Z=0;Z<T.length;Z++){let Q=S[Z];Q!==null&&(S[Z]=null,T[Z].disconnect(Q))}D=null,B=null,f.reset();for(let Z in m)delete m[Z];if(e.setRenderTarget(b),p=null,d=null,u=null,i=null,x=null,mt.stop(),n.isPresenting=!1,e.setPixelRatio(y),e.setSize(A.width,A.height,!1),E!==null){let Z=E.camera;Z.fov=E.fov,Z.zoom=E.zoom,Z.updateProjectionMatrix(),E=null}n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(Z){r=Z,n.isPresenting===!0&&Le("WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(Z){o=Z,n.isPresenting===!0&&Le("WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return l||a},this.setReferenceSpace=function(Z){l=Z},this.getBaseLayer=function(){return d!==null?d:p},this.getBinding=function(){return u===null&&v&&(u=new XRWebGLBinding(i,t)),u},this.getFrame=function(){return g},this.getSession=function(){return i},this.setSession=async function(Z){if(i=Z,i!==null){if(b=e.getRenderTarget(),i.addEventListener("select",X),i.addEventListener("selectstart",X),i.addEventListener("selectend",X),i.addEventListener("squeeze",X),i.addEventListener("squeezestart",X),i.addEventListener("squeezeend",X),i.addEventListener("end",W),i.addEventListener("inputsourceschange",re),_.xrCompatible!==!0&&await t.makeXRCompatible(),y=e.getPixelRatio(),e.getSize(A),v&&"createProjectionLayer"in XRWebGLBinding.prototype){let _e=null,We=null,be=null;_.depth&&(be=_.stencil?t.DEPTH24_STENCIL8:t.DEPTH_COMPONENT24,_e=_.stencil?ds:yi,We=_.stencil?Dr:oi);let Xe={colorFormat:t.RGBA8,depthFormat:be,scaleFactor:r};u=this.getBinding(),d=u.createProjectionLayer(Xe),i.updateRenderState({layers:[d]}),e.setPixelRatio(1),e.setSize(d.textureWidth,d.textureHeight,!1),x=new Jt(d.textureWidth,d.textureHeight,{format:Un,type:bn,depthTexture:new as(d.textureWidth,d.textureHeight,We,void 0,void 0,void 0,void 0,void 0,void 0,_e),stencilBuffer:_.stencil,colorSpace:e.outputColorSpace,samples:_.antialias?4:0,resolveDepthBuffer:d.ignoreDepthValues===!1,resolveStencilBuffer:d.ignoreDepthValues===!1,storeMultisampledDepthBuffer:d.ignoreDepthValues===!1,storeMultisampledStencilBuffer:d.ignoreDepthValues===!1})}else{let _e={antialias:_.antialias,alpha:!0,depth:_.depth,stencil:_.stencil,framebufferScaleFactor:r};p=new XRWebGLLayer(i,t,_e),i.updateRenderState({baseLayer:p}),e.setPixelRatio(1),e.setSize(p.framebufferWidth,p.framebufferHeight,!1),x=new Jt(p.framebufferWidth,p.framebufferHeight,{format:Un,type:bn,colorSpace:e.outputColorSpace,stencilBuffer:_.stencil,resolveDepthBuffer:p.ignoreDepthValues===!1,resolveStencilBuffer:p.ignoreDepthValues===!1,storeMultisampledDepthBuffer:p.ignoreDepthValues===!1,storeMultisampledStencilBuffer:p.ignoreDepthValues===!1})}x.isXRRenderTarget=!0,this.setFoveation(c),l=null,a=await i.requestReferenceSpace(o),mt.setContext(i),mt.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(i!==null)return i.environmentBlendMode},this.getDepthTexture=function(){return f.getDepthTexture()};function re(Z){for(let Q=0;Q<Z.removed.length;Q++){let _e=Z.removed[Q],We=S.indexOf(_e);We>=0&&(S[We]=null,T[We].disconnect(_e))}for(let Q=0;Q<Z.added.length;Q++){let _e=Z.added[Q],We=S.indexOf(_e);if(We===-1){for(let Xe=0;Xe<T.length;Xe++)if(Xe>=S.length){S.push(_e),We=Xe;break}else if(S[Xe]===null){S[Xe]=_e,We=Xe;break}if(We===-1)break}let be=T[We];be&&be.connect(_e)}}let q=new R,j=new R;function te(Z,Q,_e){q.setFromMatrixPosition(Q.matrixWorld),j.setFromMatrixPosition(_e.matrixWorld);let We=q.distanceTo(j),be=Q.projectionMatrix.elements,Xe=_e.projectionMatrix.elements,Tt=be[14]/(be[10]-1),ee=be[14]/(be[10]+1),ae=(be[9]+1)/be[5],oe=(be[9]-1)/be[5],le=(be[8]-1)/be[0],ue=(Xe[8]+1)/Xe[0],ze=Tt*le,Be=Tt*ue,qe=We/(-le+ue),$e=qe*-le;if(Q.matrixWorld.decompose(Z.position,Z.quaternion,Z.scale),Z.translateX($e),Z.translateZ(qe),Z.matrixWorld.compose(Z.position,Z.quaternion,Z.scale),Z.matrixWorldInverse.copy(Z.matrixWorld).invert(),be[10]===-1)Z.projectionMatrix.copy(Q.projectionMatrix),Z.projectionMatrixInverse.copy(Q.projectionMatrixInverse);else{let P=Tt+qe,Mt=ee+qe,ht=ze-$e,C=Be+(We-$e),M=ae*ee/Mt*P,O=oe*ee/Mt*P;Z.projectionMatrix.makePerspective(ht,C,M,O,P,Mt),Z.projectionMatrixInverse.copy(Z.projectionMatrix).invert()}}function Ne(Z,Q){Q===null?Z.matrixWorld.copy(Z.matrix):Z.matrixWorld.multiplyMatrices(Q.matrixWorld,Z.matrix),Z.matrixWorldInverse.copy(Z.matrixWorld).invert()}this.updateCamera=function(Z){if(i===null)return;let Q=Z.near,_e=Z.far;f.texture!==null&&(f.depthNear>0&&(Q=f.depthNear),f.depthFar>0&&(_e=f.depthFar)),V.near=L.near=I.near=Q,V.far=L.far=I.far=_e,(D!==V.near||B!==V.far)&&(i.updateRenderState({depthNear:V.near,depthFar:V.far}),D=V.near,B=V.far),V.layers.mask=Z.layers.mask|6,I.layers.mask=V.layers.mask&-5,L.layers.mask=V.layers.mask&-3;let We=Z.parent,be=V.cameras;Ne(V,We);for(let Xe=0;Xe<be.length;Xe++)Ne(be[Xe],We);be.length===2?te(V,I,L):V.projectionMatrix.copy(I.projectionMatrix),E===null&&Z.isPerspectiveCamera&&(E={camera:Z,fov:Z.fov,zoom:Z.zoom}),Ae(Z,V,We)};function Ae(Z,Q,_e){_e===null?Z.matrix.copy(Q.matrixWorld):(Z.matrix.copy(_e.matrixWorld),Z.matrix.invert(),Z.matrix.multiply(Q.matrixWorld)),Z.matrix.decompose(Z.position,Z.quaternion,Z.scale),Z.updateMatrixWorld(!0),Z.projectionMatrix.copy(Q.projectionMatrix),Z.projectionMatrixInverse.copy(Q.projectionMatrixInverse),Z.isPerspectiveCamera&&(Z.fov=As*2*Math.atan(1/Z.projectionMatrix.elements[5]),Z.zoom=1)}this.getCamera=function(){return V},this.getFoveation=function(){if(!(d===null&&p===null))return c},this.setFoveation=function(Z){c=Z,d!==null&&(d.fixedFoveation=Z),p!==null&&p.fixedFoveation!==void 0&&(p.fixedFoveation=Z)},this.hasDepthSensing=function(){return f.texture!==null},this.getDepthSensingMesh=function(){return f.getMesh(V)},this.getCameraTexture=function(Z){return m[Z]};let vt=null;function ct(Z,Q){if(h=Q.getViewerPose(l||a),g=Q,h!==null){let _e=h.views;p!==null&&(e.setRenderTargetFramebuffer(x,p.framebuffer),e.setRenderTarget(x));let We=!1;_e.length!==V.cameras.length&&(V.cameras.length=0,We=!0);for(let ee=0;ee<_e.length;ee++){let ae=_e[ee],oe=null;if(p!==null)oe=p.getViewport(ae);else{let ue=u.getViewSubImage(d,ae);oe=ue.viewport,ee===0&&(e.setRenderTargetTextures(x,ue.colorTexture,ue.depthStencilTexture),e.setRenderTarget(x))}let le=F[ee];le===void 0&&(le=new zt,le.layers.enable(ee),le.viewport=new At,F[ee]=le),le.matrix.fromArray(ae.transform.matrix),le.matrix.decompose(le.position,le.quaternion,le.scale),le.projectionMatrix.fromArray(ae.projectionMatrix),le.projectionMatrixInverse.copy(le.projectionMatrix).invert(),le.viewport.set(oe.x,oe.y,oe.width,oe.height),ee===0&&(V.matrix.copy(le.matrix),V.matrix.decompose(V.position,V.quaternion,V.scale)),We===!0&&V.cameras.push(le)}let be=i.enabledFeatures;if(be&&be.includes("depth-sensing")&&i.depthUsage=="gpu-optimized"&&v){u=n.getBinding();let ee=u.getDepthInformation(_e[0]);ee&&ee.isValid&&ee.texture&&f.init(ee,i.renderState)}if(be&&be.includes("camera-access")&&v){e.state.unbindTexture(),u=n.getBinding();for(let ee=0;ee<_e.length;ee++){let ae=_e[ee].camera;if(ae){let oe=m[ae];oe||(oe=new xa,m[ae]=oe);let le=u.getCameraImage(ae);oe.sourceTexture=le}}}}for(let _e=0;_e<T.length;_e++){let We=S[_e],be=T[_e];We!==null&&be!==void 0&&be.update(We,Q,l||a)}vt&&vt(Z,Q),Q.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:Q}),g=null}let mt=new Cp;mt.setAnimationLoop(ct),this.setAnimationLoop=function(Z){vt=Z},this.dispose=function(){}}},Zv=new je,Dp=new Ze;Dp.set(-1,0,0,0,1,0,0,0,1);function Jv(s,e){function t(f,m){f.matrixAutoUpdate===!0&&f.updateMatrix(),m.value.copy(f.matrix)}function n(f,m){m.color.getRGB(f.fogColor.value,iu(s)),m.isFog?(f.fogNear.value=m.near,f.fogFar.value=m.far):m.isFogExp2&&(f.fogDensity.value=m.density)}function i(f,m,_,b,x){m.isNodeMaterial?m.uniformsNeedUpdate=!1:m.isMeshBasicMaterial?r(f,m):m.isMeshLambertMaterial?(r(f,m),m.envMap&&(f.envMapIntensity.value=m.envMapIntensity)):m.isMeshToonMaterial?(r(f,m),u(f,m)):m.isMeshPhongMaterial?(r(f,m),h(f,m),m.envMap&&(f.envMapIntensity.value=m.envMapIntensity)):m.isMeshStandardMaterial?(r(f,m),d(f,m),m.isMeshPhysicalMaterial&&p(f,m,x)):m.isMeshMatcapMaterial?(r(f,m),g(f,m)):m.isMeshDepthMaterial?r(f,m):m.isMeshDistanceMaterial?(r(f,m),v(f,m)):m.isMeshNormalMaterial?r(f,m):m.isLineBasicMaterial?(a(f,m),m.isLineDashedMaterial&&o(f,m)):m.isPointsMaterial?c(f,m,_,b):m.isSpriteMaterial?l(f,m):m.isShadowMaterial?(f.color.value.copy(m.color),f.opacity.value=m.opacity):m.isShaderMaterial&&(m.uniformsNeedUpdate=!1)}function r(f,m){f.opacity.value=m.opacity,m.color&&f.diffuse.value.copy(m.color),m.emissive&&f.emissive.value.copy(m.emissive).multiplyScalar(m.emissiveIntensity),m.map&&(f.map.value=m.map,t(m.map,f.mapTransform)),m.alphaMap&&(f.alphaMap.value=m.alphaMap,t(m.alphaMap,f.alphaMapTransform)),m.bumpMap&&(f.bumpMap.value=m.bumpMap,t(m.bumpMap,f.bumpMapTransform),f.bumpScale.value=m.bumpScale,m.side===qt&&(f.bumpScale.value*=-1)),m.normalMap&&(f.normalMap.value=m.normalMap,t(m.normalMap,f.normalMapTransform),f.normalScale.value.copy(m.normalScale),m.side===qt&&f.normalScale.value.negate()),m.displacementMap&&(f.displacementMap.value=m.displacementMap,t(m.displacementMap,f.displacementMapTransform),f.displacementScale.value=m.displacementScale,f.displacementBias.value=m.displacementBias),m.emissiveMap&&(f.emissiveMap.value=m.emissiveMap,t(m.emissiveMap,f.emissiveMapTransform)),m.specularMap&&(f.specularMap.value=m.specularMap,t(m.specularMap,f.specularMapTransform)),m.alphaTest>0&&(f.alphaTest.value=m.alphaTest);let _=e.get(m),b=_.envMap,x=_.envMapRotation;b&&(f.envMap.value=b,f.envMapRotation.value.setFromMatrix4(Zv.makeRotationFromEuler(x)).transpose(),b.isCubeTexture&&b.isRenderTargetTexture===!1&&f.envMapRotation.value.premultiply(Dp),f.reflectivity.value=m.reflectivity,f.ior.value=m.ior,f.refractionRatio.value=m.refractionRatio),m.lightMap&&(f.lightMap.value=m.lightMap,f.lightMapIntensity.value=m.lightMapIntensity,t(m.lightMap,f.lightMapTransform)),m.aoMap&&(f.aoMap.value=m.aoMap,f.aoMapIntensity.value=m.aoMapIntensity,t(m.aoMap,f.aoMapTransform))}function a(f,m){f.diffuse.value.copy(m.color),f.opacity.value=m.opacity,m.map&&(f.map.value=m.map,t(m.map,f.mapTransform))}function o(f,m){f.dashSize.value=m.dashSize,f.totalSize.value=m.dashSize+m.gapSize,f.scale.value=m.scale}function c(f,m,_,b){f.diffuse.value.copy(m.color),f.opacity.value=m.opacity,f.size.value=m.size*_,f.scale.value=b*.5,m.map&&(f.map.value=m.map,t(m.map,f.uvTransform)),m.alphaMap&&(f.alphaMap.value=m.alphaMap,t(m.alphaMap,f.alphaMapTransform)),m.alphaTest>0&&(f.alphaTest.value=m.alphaTest)}function l(f,m){f.diffuse.value.copy(m.color),f.opacity.value=m.opacity,f.rotation.value=m.rotation,m.map&&(f.map.value=m.map,t(m.map,f.mapTransform)),m.alphaMap&&(f.alphaMap.value=m.alphaMap,t(m.alphaMap,f.alphaMapTransform)),m.alphaTest>0&&(f.alphaTest.value=m.alphaTest)}function h(f,m){f.specular.value.copy(m.specular),f.shininess.value=Math.max(m.shininess,1e-4)}function u(f,m){m.gradientMap&&(f.gradientMap.value=m.gradientMap)}function d(f,m){f.metalness.value=m.metalness,m.metalnessMap&&(f.metalnessMap.value=m.metalnessMap,t(m.metalnessMap,f.metalnessMapTransform)),f.roughness.value=m.roughness,m.roughnessMap&&(f.roughnessMap.value=m.roughnessMap,t(m.roughnessMap,f.roughnessMapTransform)),m.envMap&&(f.envMapIntensity.value=m.envMapIntensity)}function p(f,m,_){f.ior.value=m.ior,m.sheen>0&&(f.sheenColor.value.copy(m.sheenColor).multiplyScalar(m.sheen),f.sheenRoughness.value=m.sheenRoughness,m.sheenColorMap&&(f.sheenColorMap.value=m.sheenColorMap,t(m.sheenColorMap,f.sheenColorMapTransform)),m.sheenRoughnessMap&&(f.sheenRoughnessMap.value=m.sheenRoughnessMap,t(m.sheenRoughnessMap,f.sheenRoughnessMapTransform))),m.clearcoat>0&&(f.clearcoat.value=m.clearcoat,f.clearcoatRoughness.value=m.clearcoatRoughness,m.clearcoatMap&&(f.clearcoatMap.value=m.clearcoatMap,t(m.clearcoatMap,f.clearcoatMapTransform)),m.clearcoatRoughnessMap&&(f.clearcoatRoughnessMap.value=m.clearcoatRoughnessMap,t(m.clearcoatRoughnessMap,f.clearcoatRoughnessMapTransform)),m.clearcoatNormalMap&&(f.clearcoatNormalMap.value=m.clearcoatNormalMap,t(m.clearcoatNormalMap,f.clearcoatNormalMapTransform),f.clearcoatNormalScale.value.copy(m.clearcoatNormalScale),m.side===qt&&f.clearcoatNormalScale.value.negate())),m.dispersion>0&&(f.dispersion.value=m.dispersion),m.retroreflectivity>0&&(f.retroreflectivity.value=m.retroreflectivity),m.iridescence>0&&(f.iridescence.value=m.iridescence,f.iridescenceIOR.value=m.iridescenceIOR,f.iridescenceThicknessMinimum.value=m.iridescenceThicknessRange[0],f.iridescenceThicknessMaximum.value=m.iridescenceThicknessRange[1],m.iridescenceMap&&(f.iridescenceMap.value=m.iridescenceMap,t(m.iridescenceMap,f.iridescenceMapTransform)),m.iridescenceThicknessMap&&(f.iridescenceThicknessMap.value=m.iridescenceThicknessMap,t(m.iridescenceThicknessMap,f.iridescenceThicknessMapTransform))),m.transmission>0&&(f.transmission.value=m.transmission,f.transmissionSamplerMap.value=_.texture,f.transmissionSamplerSize.value.set(_.width,_.height),m.transmissionMap&&(f.transmissionMap.value=m.transmissionMap,t(m.transmissionMap,f.transmissionMapTransform)),f.thickness.value=m.thickness,m.thicknessMap&&(f.thicknessMap.value=m.thicknessMap,t(m.thicknessMap,f.thicknessMapTransform)),f.attenuationDistance.value=m.attenuationDistance,f.attenuationColor.value.copy(m.attenuationColor)),m.anisotropy>0&&(f.anisotropyVector.value.set(m.anisotropy*Math.cos(m.anisotropyRotation),m.anisotropy*Math.sin(m.anisotropyRotation)),m.anisotropyMap&&(f.anisotropyMap.value=m.anisotropyMap,t(m.anisotropyMap,f.anisotropyMapTransform))),f.specularIntensity.value=m.specularIntensity,f.specularColor.value.copy(m.specularColor),m.specularColorMap&&(f.specularColorMap.value=m.specularColorMap,t(m.specularColorMap,f.specularColorMapTransform)),m.specularIntensityMap&&(f.specularIntensityMap.value=m.specularIntensityMap,t(m.specularIntensityMap,f.specularIntensityMapTransform))}function g(f,m){m.matcap&&(f.matcap.value=m.matcap)}function v(f,m){let _=e.get(m).light;f.referencePosition.value.setFromMatrixPosition(_.matrixWorld),f.nearDistance.value=_.shadow.camera.near,f.farDistance.value=_.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:i}}function $v(s,e,t,n){let i={},r={},a=[],o=s.getParameter(s.MAX_UNIFORM_BUFFER_BINDINGS);function c(x,T){let S=T.program;n.uniformBlockBinding(x,S)}function l(x,T){let S=i[x.id];S===void 0&&(f(x),S=h(x),i[x.id]=S,x.addEventListener("dispose",_));let A=T.program;n.updateUBOMapping(x,A);let y=e.render.frame;r[x.id]!==y&&(d(x),r[x.id]=y)}function h(x){let T=u();x.__bindingPointIndex=T;let S=s.createBuffer(),A=x.__size,y=x.usage;return s.bindBuffer(s.UNIFORM_BUFFER,S),s.bufferData(s.UNIFORM_BUFFER,A,y),s.bindBuffer(s.UNIFORM_BUFFER,null),s.bindBufferBase(s.UNIFORM_BUFFER,T,S),S}function u(){for(let x=0;x<o;x++)if(a.indexOf(x)===-1)return a.push(x),x;return He("WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function d(x){let T=i[x.id],S=x.uniforms,A=x.__cache;s.bindBuffer(s.UNIFORM_BUFFER,T);for(let y=0,E=S.length;y<E;y++){let I=S[y];if(Array.isArray(I))for(let L=0,F=I.length;L<F;L++)p(I[L],y,L,A);else p(I,y,0,A)}s.bindBuffer(s.UNIFORM_BUFFER,null)}function p(x,T,S,A){if(v(x,T,S,A)===!0){let y=x.__offset,E=x.value;if(Array.isArray(E)){let I=0;for(let L=0;L<E.length;L++){let F=E[L],V=m(F);g(F,x.__data,I),typeof F!="number"&&typeof F!="boolean"&&!F.isMatrix3&&!ArrayBuffer.isView(F)&&(I+=V.storage/Float32Array.BYTES_PER_ELEMENT)}}else g(E,x.__data,0);s.bufferSubData(s.UNIFORM_BUFFER,y,x.__data)}}function g(x,T,S){typeof x=="number"||typeof x=="boolean"?T[0]=x:x.isMatrix3?(T[0]=x.elements[0],T[1]=x.elements[1],T[2]=x.elements[2],T[3]=0,T[4]=x.elements[3],T[5]=x.elements[4],T[6]=x.elements[5],T[7]=0,T[8]=x.elements[6],T[9]=x.elements[7],T[10]=x.elements[8],T[11]=0):ArrayBuffer.isView(x)?T.set(new x.constructor(x.buffer,x.byteOffset,T.length)):x.toArray(T,S)}function v(x,T,S,A){let y=x.value,E=T+"_"+S;if(A[E]===void 0)return typeof y=="number"||typeof y=="boolean"?A[E]=y:ArrayBuffer.isView(y)?A[E]=y.slice():A[E]=y.clone(),!0;{let I=A[E];if(typeof y=="number"||typeof y=="boolean"){if(I!==y)return A[E]=y,!0}else{if(ArrayBuffer.isView(y))return!0;if(I.equals(y)===!1)return I.copy(y),!0}}return!1}function f(x){let T=x.uniforms,S=0,A=16;for(let E=0,I=T.length;E<I;E++){let L=Array.isArray(T[E])?T[E]:[T[E]];for(let F=0,V=L.length;F<V;F++){let D=L[F],B=Array.isArray(D.value)?D.value:[D.value];for(let X=0,W=B.length;X<W;X++){let re=B[X],q=m(re),j=S%A,te=j%q.boundary,Ne=j+te;S+=te,Ne!==0&&A-Ne<q.storage&&(S+=A-Ne),D.__data=new Float32Array(q.storage/Float32Array.BYTES_PER_ELEMENT),D.__offset=S,S+=q.storage}}}let y=S%A;return y>0&&(S+=A-y),x.__size=S,x.__cache={},this}function m(x){let T={boundary:0,storage:0};return typeof x=="number"||typeof x=="boolean"?(T.boundary=4,T.storage=4):x.isVector2?(T.boundary=8,T.storage=8):x.isVector3||x.isColor?(T.boundary=16,T.storage=12):x.isVector4?(T.boundary=16,T.storage=16):x.isMatrix3?(T.boundary=48,T.storage=48):x.isMatrix4?(T.boundary=64,T.storage=64):x.isTexture?Le("WebGLRenderer: Texture samplers can not be part of an uniforms group."):ArrayBuffer.isView(x)?(T.boundary=16,T.storage=x.byteLength):Le("WebGLRenderer: Unsupported uniform value type.",x),T}function _(x){let T=x.target;T.removeEventListener("dispose",_);let S=a.indexOf(T.__bindingPointIndex);a.splice(S,1),s.deleteBuffer(i[T.id]),delete i[T.id],delete r[T.id]}function b(){for(let x in i)s.deleteBuffer(i[x]);a=[],i={},r={}}return{bind:c,update:l,dispose:b}}var jv=new Uint16Array([12469,15057,12620,14925,13266,14620,13807,14376,14323,13990,14545,13625,14713,13328,14840,12882,14931,12528,14996,12233,15039,11829,15066,11525,15080,11295,15085,10976,15082,10705,15073,10495,13880,14564,13898,14542,13977,14430,14158,14124,14393,13732,14556,13410,14702,12996,14814,12596,14891,12291,14937,11834,14957,11489,14958,11194,14943,10803,14921,10506,14893,10278,14858,9960,14484,14039,14487,14025,14499,13941,14524,13740,14574,13468,14654,13106,14743,12678,14818,12344,14867,11893,14889,11509,14893,11180,14881,10751,14852,10428,14812,10128,14765,9754,14712,9466,14764,13480,14764,13475,14766,13440,14766,13347,14769,13070,14786,12713,14816,12387,14844,11957,14860,11549,14868,11215,14855,10751,14825,10403,14782,10044,14729,9651,14666,9352,14599,9029,14967,12835,14966,12831,14963,12804,14954,12723,14936,12564,14917,12347,14900,11958,14886,11569,14878,11247,14859,10765,14828,10401,14784,10011,14727,9600,14660,9289,14586,8893,14508,8533,15111,12234,15110,12234,15104,12216,15092,12156,15067,12010,15028,11776,14981,11500,14942,11205,14902,10752,14861,10393,14812,9991,14752,9570,14682,9252,14603,8808,14519,8445,14431,8145,15209,11449,15208,11451,15202,11451,15190,11438,15163,11384,15117,11274,15055,10979,14994,10648,14932,10343,14871,9936,14803,9532,14729,9218,14645,8742,14556,8381,14461,8020,14365,7603,15273,10603,15272,10607,15267,10619,15256,10631,15231,10614,15182,10535,15118,10389,15042,10167,14963,9787,14883,9447,14800,9115,14710,8665,14615,8318,14514,7911,14411,7507,14279,7198,15314,9675,15313,9683,15309,9712,15298,9759,15277,9797,15229,9773,15166,9668,15084,9487,14995,9274,14898,8910,14800,8539,14697,8234,14590,7790,14479,7409,14367,7067,14178,6621,15337,8619,15337,8631,15333,8677,15325,8769,15305,8871,15264,8940,15202,8909,15119,8775,15022,8565,14916,8328,14804,8009,14688,7614,14569,7287,14448,6888,14321,6483,14088,6171,15350,7402,15350,7419,15347,7480,15340,7613,15322,7804,15287,7973,15229,8057,15148,8012,15046,7846,14933,7611,14810,7357,14682,7069,14552,6656,14421,6316,14251,5948,14007,5528,15356,5942,15356,5977,15353,6119,15348,6294,15332,6551,15302,6824,15249,7044,15171,7122,15070,7050,14949,6861,14818,6611,14679,6349,14538,6067,14398,5651,14189,5311,13935,4958,15359,4123,15359,4153,15356,4296,15353,4646,15338,5160,15311,5508,15263,5829,15188,6042,15088,6094,14966,6001,14826,5796,14678,5543,14527,5287,14377,4985,14133,4586,13869,4257,15360,1563,15360,1642,15358,2076,15354,2636,15341,3350,15317,4019,15273,4429,15203,4732,15105,4911,14981,4932,14836,4818,14679,4621,14517,4386,14359,4156,14083,3795,13808,3437,15360,122,15360,137,15358,285,15355,636,15344,1274,15322,2177,15281,2765,15215,3223,15120,3451,14995,3569,14846,3567,14681,3466,14511,3305,14344,3121,14037,2800,13753,2467,15360,0,15360,1,15359,21,15355,89,15346,253,15325,479,15287,796,15225,1148,15133,1492,15008,1749,14856,1882,14685,1886,14506,1783,14324,1608,13996,1398,13702,1183]),Ai=null;function Qv(){return Ai===null&&(Ai=new Sr(jv,16,16,fs,an),Ai.name="DFG_LUT",Ai.minFilter=Xt,Ai.magFilter=Xt,Ai.wrapS=rn,Ai.wrapT=rn,Ai.generateMipmaps=!1,Ai.needsUpdate=!0),Ai}var pc=class{constructor(e={}){let{canvas:t=Zf(),context:n=null,depth:i=!0,stencil:r=!1,alpha:a=!1,antialias:o=!1,premultipliedAlpha:c=!0,preserveDrawingBuffer:l=!1,powerPreference:h="default",failIfMajorPerformanceCaveat:u=!1,reversedDepthBuffer:d=!1,outputBufferType:p=bn}=e;this.isWebGLRenderer=!0;let g;if(n!==null){if(typeof WebGLRenderingContext<"u"&&n instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");g=n.getContextAttributes().alpha}else g=a;let v=p,f=new Set([Il,Rl,Cl]),m=new Set([bn,oi,Nr,Dr,wl,Al]),_=new Uint32Array(4),b=new Int32Array(4),x=new R,T=null,S=null,A=[],y=[],E=null;this.domElement=t,this.debug={checkShaderErrors:!0,diagnostics:{keywords:!1},onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=ri,this.toneMappingExposure=1,this.transmissionResolutionScale=1;let I=this,L=!1,F=null,V=null,D=null,B=null;this._outputColorSpace=Ct;let X=0,W=0,re=null,q=-1,j=null,te=new At,Ne=new At,Ae=null,vt=new Me(0),ct=0,mt=t.width,Z=t.height,Q=1,_e=null,We=null,be=new At(0,0,mt,Z),Xe=new At(0,0,mt,Z),Tt=!1,ee=new br,ae=!1,oe=!1,le=new je,ue=new R,ze=new At,Be={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0},qe=!1;function $e(){return re===null?Q:1}let P=n;function Mt(w,N){return t.getContext(w,N)}let ht,C,M,O,G,Y,ce,he,K,$,de,De,ge,fe,Ue,Ge,et,U,pe,J,me,Se,ie;try{let w={alpha:!0,depth:i,stencil:r,antialias:o,premultipliedAlpha:c,preserveDrawingBuffer:l,powerPreference:h,failIfMajorPerformanceCaveat:u};if("setAttribute"in t&&t.setAttribute("data-engine",`three.js r${"186"}`),t.addEventListener("webglcontextlost",Dt,!1),t.addEventListener("webglcontextrestored",St,!1),t.addEventListener("webglcontextcreationerror",Jn,!1),P===null){let N="webgl2";if(P=Mt(N,w),P===null)throw Mt(N)?new Error("THREE.WebGLRenderer: Error creating WebGL context with your selected attributes."):new Error("THREE.WebGLRenderer: Error creating WebGL context.")}Fe()}catch(w){throw t.removeEventListener("webglcontextlost",Dt,!1),t.removeEventListener("webglcontextrestored",St,!1),t.removeEventListener("webglcontextcreationerror",Jn,!1),He("WebGLRenderer: "+w.message),w}function Fe(){ht=new ay(P),ht.init(),me=new qv(P,ht),C=new J_(P,ht,e,me),M=new Wv(P,ht),C.reversedDepthBuffer&&d&&M.buffers.depth.setReversed(!0),V=P.createFramebuffer(),D=P.createFramebuffer(),B=P.createFramebuffer(),O=new cy(P),G=new Iv,Y=new Xv(P,ht,M,G,C,me,O),ce=new ry(I),he=new u0(P),Se=new K_(P,he),K=new oy(P,he,O,Se),$=new uy(P,K,he,Se,O),U=new hy(P,C,Y),Ue=new $_(G),de=new Rv(I,ce,ht,C,Se,Ue),De=new Jv(I,G),ge=new Lv,fe=new Bv(ht),et=new Y_(I,ce,M,$,g,c),Ge=new Hv(I,$,C),ie=new $v(P,O,C,M),pe=new Z_(P,ht,O),J=new ly(P,ht,O),O.programs=de.programs,I.capabilities=C,I.extensions=ht,I.properties=G,I.renderLists=ge,I.shadowMap=Ge,I.state=M,I.info=O}v!==bn&&(E=new fy(v,t.width,t.height,o,i,r));let Ie=new Mu(I,P);this.xr=Ie,this.getContext=function(){return P},this.getContextAttributes=function(){return P.getContextAttributes()},this.forceContextLoss=function(){let w=ht.get("WEBGL_lose_context");w&&w.loseContext()},this.forceContextRestore=function(){let w=ht.get("WEBGL_lose_context");w&&w.restoreContext()},this.getPixelRatio=function(){return Q},this.setPixelRatio=function(w){w!==void 0&&(Q=w,this.setSize(mt,Z,!1))},this.getSize=function(w){return w.set(mt,Z)},this.setSize=function(w,N,H=!0){if(Ie.isPresenting){Le("WebGLRenderer: Can't change size while VR device is presenting.");return}mt=w,Z=N,t.width=Math.floor(w*Q),t.height=Math.floor(N*Q),H===!0&&(t.style.width=w+"px",t.style.height=N+"px"),E!==null&&E.setSize(t.width,t.height),this.setViewport(0,0,w,N)},this.getDrawingBufferSize=function(w){return w.set(mt*Q,Z*Q).floor()},this.setDrawingBufferSize=function(w,N,H){mt=w,Z=N,Q=H,t.width=Math.floor(w*H),t.height=Math.floor(N*H),this.setViewport(0,0,w,N)},this.setEffects=function(w){if(v===bn){He("WebGLRenderer: setEffects() requires outputBufferType set to HalfFloatType or FloatType.");return}if(w){for(let N=0;N<w.length;N++)if(w[N].isOutputPass===!0){Le("WebGLRenderer: OutputPass is not needed in setEffects(). Tone mapping and color space conversion are applied automatically.");break}}E.setEffects(w||[])},this.getCurrentViewport=function(w){return w.copy(te)},this.getViewport=function(w){return w.copy(be)},this.setViewport=function(w,N,H,k){w.isVector4?be.set(w.x,w.y,w.z,w.w):be.set(w,N,H,k),M.viewport(te.copy(be).multiplyScalar(Q).round())},this.getScissor=function(w){return w.copy(Xe)},this.setScissor=function(w,N,H,k){w.isVector4?Xe.set(w.x,w.y,w.z,w.w):Xe.set(w,N,H,k),M.scissor(Ne.copy(Xe).multiplyScalar(Q).round())},this.getScissorTest=function(){return Tt},this.setScissorTest=function(w){M.setScissorTest(Tt=w)},this.setOpaqueSort=function(w){_e=w},this.setTransparentSort=function(w){We=w},this.getClearColor=function(w){return w.copy(et.getClearColor())},this.setClearColor=function(){et.setClearColor(...arguments)},this.getClearAlpha=function(){return et.getClearAlpha()},this.setClearAlpha=function(){et.setClearAlpha(...arguments)},this.clear=function(w=!0,N=!0,H=!0){let k=0;if(w){let z=!1;if(re!==null){let ve=re.texture.format;z=f.has(ve)}if(z){let ve=re.texture.type,we=m.has(ve),ye=et.getClearColor(),Ce=et.getClearAlpha(),Pe=ye.r,rt=ye.g,ut=ye.b;we?(_[0]=Pe,_[1]=rt,_[2]=ut,_[3]=Ce,P.clearBufferuiv(P.COLOR,0,_)):(b[0]=Pe,b[1]=rt,b[2]=ut,b[3]=Ce,P.clearBufferiv(P.COLOR,0,b))}else k|=P.COLOR_BUFFER_BIT}N&&(k|=P.DEPTH_BUFFER_BIT,this.state.buffers.depth.setMask(!0)),H&&(k|=P.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),k!==0&&P.clear(k)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.setNodesHandler=function(w){w.setRenderer(this),F=w},this.dispose=function(){t.removeEventListener("webglcontextlost",Dt,!1),t.removeEventListener("webglcontextrestored",St,!1),t.removeEventListener("webglcontextcreationerror",Jn,!1),et.dispose(),ge.dispose(),fe.dispose(),G.dispose(),ce.dispose(),$.dispose(),Se.dispose(),ie.dispose(),de.dispose(),Ie.dispose(),Ie.removeEventListener("sessionstart",pd),Ie.removeEventListener("sessionend",md),_s.stop()};function Dt(w){w.preventDefault(),oa("WebGLRenderer: Context Lost."),L=!0}function St(){oa("WebGLRenderer: Context Restored."),L=!1;let w=O.autoReset,N=Ge.enabled,H=Ge.autoUpdate,k=Ge.needsUpdate,z=Ge.type;Fe(),O.autoReset=w,Ge.enabled=N,Ge.autoUpdate=H,Ge.needsUpdate=k,Ge.type=z}function Jn(w){He("WebGLRenderer: A WebGL context could not be created. Reason: ",w.statusMessage)}function ui(w){let N=w.target;N.removeEventListener("dispose",ui),Am(N)}function Am(w){Em(w),G.remove(w)}function Em(w){let N=G.get(w).programs;N!==void 0&&(N.forEach(function(H){de.releaseProgram(H)}),w.isShaderMaterial&&de.releaseShaderCache(w))}this.renderBufferDirect=function(w,N,H,k,z,ve){N===null&&(N=Be);let we=z.isMesh&&z.matrixWorld.determinantAffine()<0,ye=Im(w,N,H,k,z);M.setMaterial(k,we);let Ce=H.index,Pe=1;if(k.wireframe===!0){if(Ce=K.getWireframeAttribute(H),Ce===void 0)return;Pe=2}let rt=H.drawRange,ut=H.attributes.position,Re=rt.start*Pe,bt=(rt.start+rt.count)*Pe;ve!==null&&(Re=Math.max(Re,ve.start*Pe),bt=Math.min(bt,(ve.start+ve.count)*Pe)),Ce!==null?(Re=Math.max(Re,0),bt=Math.min(bt,Ce.count)):ut!=null&&(Re=Math.max(Re,0),bt=Math.min(bt,ut.count));let Kt=bt-Re;if(Kt<0||Kt===1/0)return;Se.setup(z,k,ye,H,Ce);let Ot,Pt=pe;if(Ce!==null&&(Ot=he.get(Ce),Pt=J,Pt.setIndex(Ot)),z.isMesh)k.wireframe===!0?(M.setLineWidth(k.wireframeLinewidth*$e()),Pt.setMode(P.LINES)):Pt.setMode(P.TRIANGLES);else if(z.isLine){let ln=k.linewidth;ln===void 0&&(ln=1),M.setLineWidth(ln*$e()),z.isLineSegments?Pt.setMode(P.LINES):z.isLineLoop?Pt.setMode(P.LINE_LOOP):Pt.setMode(P.LINE_STRIP)}else z.isPoints?Pt.setMode(P.POINTS):z.isSprite&&Pt.setMode(P.TRIANGLES);if(z.isBatchedMesh)if(ht.get("WEBGL_multi_draw"))Pt.renderMultiDraw(z._multiDrawStarts,z._multiDrawCounts,z._multiDrawCount);else{let ln=z._multiDrawStarts,Te=z._multiDrawCounts,pn=z._multiDrawCount,gt=Ce?he.get(Ce).bytesPerElement:1,On=G.get(k).currentProgram.getUniforms();for(let di=0;di<pn;di++)On.setValue(P,"_gl_DrawID",di),Pt.render(ln[di]/gt,Te[di])}else if(z.isInstancedMesh)Pt.renderInstances(Re,Kt,z.count);else if(H.isInstancedBufferGeometry){let ln=H._maxInstanceCount!==void 0?H._maxInstanceCount:1/0,Te=Math.min(H.instanceCount,ln);Pt.renderInstances(Re,Kt,Te)}else Pt.render(Re,Kt)};function fd(w,N,H,k){F!==null&&w.isNodeMaterial&&F.setObject(k,w),ae===!0&&Ue.setState(w,H,!1),w.transparent===!0&&w.side===st&&w.forceSinglePass===!1?(w.side=qt,w.needsUpdate=!0,co(w,N,k),w.side=wi,w.needsUpdate=!0,co(w,N,k),w.side=st):co(w,N,k)}this.compile=function(w,N,H=null){H===null&&(H=w),F!==null&&F.renderStart(w,N,H),S=fe.get(H),S.init(N),y.push(S),H.traverseVisible(function(z){z.isLight&&z.layers.test(N.layers)&&(S.pushLight(z),z.castShadow&&S.pushShadow(z))}),w!==H&&w.traverseVisible(function(z){z.isLight&&z.layers.test(N.layers)&&(S.pushLight(z),z.castShadow&&S.pushShadow(z))}),S.setupLights(),F!==null&&F.updateLights(S.state.lightsArray),oe=this.localClippingEnabled,ae=Ue.init(this.clippingPlanes,oe),ae===!0&&Ue.setGlobalState(this.clippingPlanes,N),F!==null&&Ge.render(S.state.shadowsArray,H,N);let k=new Set;return w.traverse(function(z){if(!(z.isMesh||z.isPoints||z.isLine||z.isSprite))return;let ve=z.material;if(ve)if(Array.isArray(ve))for(let we=0;we<ve.length;we++){let ye=ve[we];fd(ye,H,N,z),k.add(ye)}else fd(ve,H,N,z),k.add(ve)}),S=y.pop(),F!==null&&F.renderEnd(),k},this.compileAsync=function(w,N,H=null){let k=this.compile(w,N,H);return new Promise(z=>{function ve(){if(k.forEach(function(we){let Ce=G.get(we).currentProgram;(Ce===void 0||Ce.isReady())&&k.delete(we)}),k.size===0){z(w);return}setTimeout(ve,10)}ht.get("KHR_parallel_shader_compile")!==null?ve():setTimeout(ve,10)})};let qc=null;function Cm(w){qc&&qc(w)}function pd(){_s.stop()}function md(){_s.start()}let _s=new Cp;_s.setAnimationLoop(Cm),typeof self<"u"&&_s.setContext(self),this.setAnimationLoop=function(w){qc=w,Ie.setAnimationLoop(w),w===null?_s.stop():_s.start()},Ie.addEventListener("sessionstart",pd),Ie.addEventListener("sessionend",md),this.render=function(w,N){if(N!==void 0&&N.isCamera!==!0){He("WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(L===!0)return;F!==null&&F.renderStart(w,N);let H=Ie.enabled===!0&&Ie.isPresenting===!0,k=E!==null&&(re===null||H)&&E.begin(I,re);if(w.matrixWorldAutoUpdate===!0&&w.updateMatrixWorld(),N.parent===null&&N.matrixWorldAutoUpdate===!0&&N.updateMatrixWorld(),Ie.enabled===!0&&Ie.isPresenting===!0&&(E===null||E.isCompositing()===!1)&&(Ie.cameraAutoUpdate===!0&&Ie.updateCamera(N),N=Ie.getCamera()),w.isScene===!0&&w.onBeforeRender(I,w,N,re),S=fe.get(w,y.length),S.init(N),S.state.textureUnits=Y.getTextureUnits(),y.push(S),le.multiplyMatrices(N.projectionMatrix,N.matrixWorldInverse),ee.setFromProjectionMatrix(le,ni,N.reversedDepth),oe=this.localClippingEnabled,ae=Ue.init(this.clippingPlanes,oe),T=ge.get(w,A.length),T.init(),A.push(T),Ie.enabled===!0&&Ie.isPresenting===!0){let we=I.xr.getDepthSensingMesh();we!==null&&Yc(we,N,-1/0,I.sortObjects)}Yc(w,N,0,I.sortObjects),T.finish(),F!==null&&F.updateLights(S.state.lightsArray),I.sortObjects===!0&&T.sort(_e,We),qe=Ie.enabled===!1||Ie.isPresenting===!1||Ie.hasDepthSensing()===!1,qe&&et.addToRenderList(T,w),this.info.render.frame++,this.info.autoReset===!0&&this.info.reset(),ae===!0&&Ue.beginShadows();let z=S.state.shadowsArray;if(Ge.render(z,w,N),ae===!0&&Ue.endShadows(),(k&&E.hasRenderPass())===!1){let we=T.opaque,ye=T.transmissive;if(S.setupLights(),N.isArrayCamera){let Ce=N.cameras;if(ye.length>0)for(let Pe=0,rt=Ce.length;Pe<rt;Pe++){let ut=Ce[Pe];xd(we,ye,w,ut)}qe&&et.render(w);for(let Pe=0,rt=Ce.length;Pe<rt;Pe++){let ut=Ce[Pe];gd(T,w,ut,ut.viewport)}}else ye.length>0&&xd(we,ye,w,N),qe&&et.render(w),gd(T,w,N)}re!==null&&W===0&&(Y.updateMultisampleRenderTarget(re),Y.updateRenderTargetMipmap(re)),k&&E.end(I),w.isScene===!0&&w.onAfterRender(I,w,N),Se.resetDefaultState(),q=-1,j=null,y.pop(),y.length>0?(S=y[y.length-1],Y.setTextureUnits(S.state.textureUnits),ae===!0&&Ue.setGlobalState(I.clippingPlanes,S.state.camera)):S=null,A.pop(),A.length>0?T=A[A.length-1]:T=null,F!==null&&F.renderEnd()};function Yc(w,N,H,k){if(w.visible===!1)return;if(w.layers.test(N.layers)){if(w.isGroup)H=w.renderOrder;else if(w.isLOD)w.autoUpdate===!0&&w.update(N);else if(w.isLightProbeGrid)S.pushLightProbeGrid(w);else if(w.isLight)S.pushLight(w),w.castShadow&&S.pushShadow(w);else if(w.isSprite){if(!w.frustumCulled||w.intersectsFrustum(ee)){k&&ze.setFromMatrixPosition(w.matrixWorld).applyMatrix4(le);let we=$.update(w),ye=w.material;ye.visible&&T.push(w,we,ye,H,ze.z,null,N)}}else if((w.isMesh||w.isLine||w.isPoints)&&(!w.frustumCulled||w.intersectsFrustum(ee))){let we=$.update(w),ye=w.material;if(k&&(w.boundingSphere!==void 0?(w.boundingSphere===null&&w.computeBoundingSphere(),ze.copy(w.boundingSphere.center)):(we.boundingSphere===null&&we.computeBoundingSphere(),ze.copy(we.boundingSphere.center)),ze.applyMatrix4(w.matrixWorld).applyMatrix4(le)),Array.isArray(ye)){let Ce=we.groups;for(let Pe=0,rt=Ce.length;Pe<rt;Pe++){let ut=Ce[Pe],Re=ye[ut.materialIndex];Re&&Re.visible&&T.push(w,we,Re,H,ze.z,ut,N)}}else ye.visible&&T.push(w,we,ye,H,ze.z,null,N)}}let ve=w.children;for(let we=0,ye=ve.length;we<ye;we++)Yc(ve[we],N,H,k)}function gd(w,N,H,k){let{opaque:z,transmissive:ve,transparent:we}=w;S.setupLightsView(H),ae===!0&&Ue.setGlobalState(I.clippingPlanes,H),k&&M.viewport(te.copy(k)),z.length>0&&lo(z,N,H),ve.length>0&&lo(ve,N,H),we.length>0&&lo(we,N,H),M.buffers.depth.setTest(!0),M.buffers.depth.setMask(!0),M.buffers.color.setMask(!0),M.setPolygonOffset(!1)}function xd(w,N,H,k){if((H.isScene===!0?H.overrideMaterial:null)!==null)return;if(S.state.transmissionRenderTarget[k.id]===void 0){let Re=ht.has("EXT_color_buffer_half_float")||ht.has("EXT_color_buffer_float");S.state.transmissionRenderTarget[k.id]=new Jt(1,1,{generateMipmaps:!0,type:Re?an:bn,minFilter:ai,samples:Math.max(4,C.samples),stencilBuffer:r,resolveDepthBuffer:!1,resolveStencilBuffer:!1,storeMultisampledDepthBuffer:!1,storeMultisampledStencilBuffer:!1,colorSpace:it.workingColorSpace})}let ve=S.state.transmissionRenderTarget[k.id],we=k.viewport||te;ve.setSize(we.z*I.transmissionResolutionScale,we.w*I.transmissionResolutionScale);let ye=I.getRenderTarget(),Ce=I.getActiveCubeFace(),Pe=I.getActiveMipmapLevel();I.setRenderTarget(ve),I.getClearColor(vt),ct=I.getClearAlpha(),ct<1&&I.setClearColor(16777215,.5),I.clear(),qe&&et.render(H);let rt=I.toneMapping;I.toneMapping=ri;let ut=k.viewport;if(k.viewport!==void 0&&(k.viewport=void 0),S.setupLightsView(k),ae===!0&&Ue.setGlobalState(I.clippingPlanes,k),lo(w,H,k),Y.updateMultisampleRenderTarget(ve),Y.updateRenderTargetMipmap(ve),ht.has("WEBGL_multisampled_render_to_texture")===!1){let Re=!1;for(let bt=0,Kt=N.length;bt<Kt;bt++){let Ot=N[bt],{object:Pt,geometry:ln,material:Te,group:pn}=Ot;if(Te.side===st&&Pt.layers.test(k.layers)){let gt=Te.side;Te.side=qt,Te.needsUpdate=!0,_d(Pt,H,k,ln,Te,pn),Te.side=gt,Te.needsUpdate=!0,Re=!0}}Re===!0&&(Y.updateMultisampleRenderTarget(ve),Y.updateRenderTargetMipmap(ve))}I.setRenderTarget(ye,Ce,Pe),I.setClearColor(vt,ct),ut!==void 0&&(k.viewport=ut),I.toneMapping=rt}function lo(w,N,H){let k=N.isScene===!0?N.overrideMaterial:null;for(let z=0,ve=w.length;z<ve;z++){let we=w[z],{object:ye,geometry:Ce,group:Pe}=we,rt=we.material;rt.allowOverride===!0&&k!==null&&(rt=k),ye.layers.test(H.layers)&&_d(ye,N,H,Ce,rt,Pe)}}function _d(w,N,H,k,z,ve){F!==null&&z.isNodeMaterial&&F.setObject(w,z),w.onBeforeRender(I,N,H,k,z,ve),w.modelViewMatrix.multiplyMatrices(H.matrixWorldInverse,w.matrixWorld),w.normalMatrix.getNormalMatrix(w.modelViewMatrix),z.onBeforeRender(I,N,H,k,w,ve),z.transparent===!0&&z.side===st&&z.forceSinglePass===!1?(z.side=qt,z.needsUpdate=!0,I.renderBufferDirect(H,N,k,z,w,ve),z.side=wi,z.needsUpdate=!0,I.renderBufferDirect(H,N,k,z,w,ve),z.side=st):I.renderBufferDirect(H,N,k,z,w,ve),w.onAfterRender(I,N,H,k,z,ve)}function co(w,N,H){N.isScene!==!0&&(N=Be);let k=G.get(w),z=S.state.lights,ve=S.state.shadowsArray,we=z.state.version,ye=de.getParameters(w,z.state,ve,N,H,S.state.lightProbeGridArray),Ce=de.getProgramCacheKey(ye),Pe=k.programs;k.environment=w.isMeshStandardMaterial||w.isMeshLambertMaterial||w.isMeshPhongMaterial?N.environment:null,k.fog=N.fog;let rt=w.isMeshStandardMaterial||w.isMeshLambertMaterial&&!w.envMap||w.isMeshPhongMaterial&&!w.envMap;k.envMap=ce.get(w.envMap||k.environment,rt),k.envMapRotation=k.environment!==null&&w.envMap===null?N.environmentRotation:w.envMapRotation,Pe===void 0&&(w.addEventListener("dispose",ui),Pe=new Map,k.programs=Pe);let ut=Pe.get(Ce);if(ut!==void 0){if(k.currentProgram===ut&&k.lightsStateVersion===we)return vd(w,ye),ut}else ye.uniforms=de.getUniforms(w),F!==null&&w.isNodeMaterial&&F.build(w,H,ye),w.onBeforeCompile(ye,I),ut=de.acquireProgram(ye,Ce),Pe.set(Ce,ut),k.uniforms=ye.uniforms;let Re=k.uniforms;return(!w.isShaderMaterial&&!w.isRawShaderMaterial||w.clipping===!0)&&(Re.clippingPlanes=Ue.uniform),vd(w,ye),k.needsLights=Lm(w),k.lightsStateVersion=we,k.needsLights&&(Re.ambientLightColor.value=z.state.ambient,Re.lightProbe.value=z.state.probe,Re.sunLights.value=z.state.sun,Re.sunLightShadows.value=z.state.sunShadow,Re.directionalLights.value=z.state.directional,Re.directionalLightShadows.value=z.state.directionalShadow,Re.spotLights.value=z.state.spot,Re.spotLightShadows.value=z.state.spotShadow,Re.rectAreaLights.value=z.state.rectArea,Re.ltc_1.value=z.state.rectAreaLTC1,Re.ltc_2.value=z.state.rectAreaLTC2,Re.pointLights.value=z.state.point,Re.pointLightShadows.value=z.state.pointShadow,Re.hemisphereLights.value=z.state.hemi,Re.sunShadowMatrix.value=z.state.sunShadowMatrix,Re.sunShadowCascade.value=z.state.sunShadowCascade,Re.directionalShadowMatrix.value=z.state.directionalShadowMatrix,Re.spotLightMatrix.value=z.state.spotLightMatrix,Re.spotLightMap.value=z.state.spotLightMap,Re.pointShadowMatrix.value=z.state.pointShadowMatrix),k.lightProbeGrid=S.state.lightProbeGridArray.length>0,k.currentProgram=ut,k.uniformsList=null,ut}function yd(w){if(w.uniformsList===null){let N=w.currentProgram.getUniforms();w.uniformsList=Br.seqWithValue(N.seq,w.uniforms)}return w.uniformsList}function vd(w,N){let H=G.get(w);H.outputColorSpace=N.outputColorSpace,H.batching=N.batching,H.batchingColor=N.batchingColor,H.instancing=N.instancing,H.instancingColor=N.instancingColor,H.instancingMorph=N.instancingMorph,H.skinning=N.skinning,H.morphTargets=N.morphTargets,H.morphNormals=N.morphNormals,H.morphColors=N.morphColors,H.morphTargetsCount=N.morphTargetsCount,H.numClippingPlanes=N.numClippingPlanes,H.numIntersection=N.numClipIntersection,H.vertexAlphas=N.vertexAlphas,H.vertexTangents=N.vertexTangents,H.toneMapping=N.toneMapping}function Rm(w,N){if(w.length===0)return null;if(w.length===1)return w[0].texture!==null?w[0]:null;x.setFromMatrixPosition(N.matrixWorld);for(let H=0,k=w.length;H<k;H++){let z=w[H];if(z.texture!==null&&z.boundingBox.containsPoint(x))return z}return null}function Im(w,N,H,k,z){N.isScene!==!0&&(N=Be),Y.resetTextureUnits();let ve=N.fog,we=k.isMeshStandardMaterial||k.isMeshLambertMaterial||k.isMeshPhongMaterial?N.environment:null,ye=re===null?I.outputColorSpace:re.isXRRenderTarget===!0?re.texture.colorSpace:it.workingColorSpace,Ce=k.isMeshStandardMaterial||k.isMeshLambertMaterial&&!k.envMap||k.isMeshPhongMaterial&&!k.envMap,Pe=ce.get(k.envMap||we,Ce),rt=k.vertexColors===!0&&!!H.attributes.color&&H.attributes.color.itemSize===4,ut=!!H.attributes.tangent&&(!!k.normalMap||k.anisotropy>0),Re=!!H.morphAttributes.position,bt=!!H.morphAttributes.normal,Kt=!!H.morphAttributes.color,Ot=ri;k.toneMapped&&(re===null||re.isXRRenderTarget===!0)&&(Ot=I.toneMapping);let Pt=H.morphAttributes.position||H.morphAttributes.normal||H.morphAttributes.color,ln=Pt!==void 0?Pt.length:0,Te=G.get(k),pn=S.state.lights;if(ae===!0&&(oe===!0||w!==j)){let Ut=w===j&&k.id===q;Ue.setState(k,w,Ut)}let gt=!1;k.version===Te.__version?(Te.needsLights&&Te.lightsStateVersion!==pn.state.version||Te.outputColorSpace!==ye||z.isBatchedMesh&&Te.batching===!1||!z.isBatchedMesh&&Te.batching===!0||z.isBatchedMesh&&Te.batchingColor===!0&&z._colorsTexture===null||z.isBatchedMesh&&Te.batchingColor===!1&&z._colorsTexture!==null||z.isInstancedMesh&&Te.instancing===!1||!z.isInstancedMesh&&Te.instancing===!0||z.isSkinnedMesh&&Te.skinning===!1||!z.isSkinnedMesh&&Te.skinning===!0||z.isInstancedMesh&&Te.instancingColor===!0&&z.instanceColor===null||z.isInstancedMesh&&Te.instancingColor===!1&&z.instanceColor!==null||z.isInstancedMesh&&Te.instancingMorph===!0&&z.morphTexture===null||z.isInstancedMesh&&Te.instancingMorph===!1&&z.morphTexture!==null||Te.envMap!==Pe||k.fog===!0&&Te.fog!==ve||Te.numClippingPlanes!==void 0&&(Te.numClippingPlanes!==Ue.numPlanes||Te.numIntersection!==Ue.numIntersection)||Te.vertexAlphas!==rt||Te.vertexTangents!==ut||Te.morphTargets!==Re||Te.morphNormals!==bt||Te.morphColors!==Kt||Te.toneMapping!==Ot||Te.morphTargetsCount!==ln||!!Te.lightProbeGrid!=S.state.lightProbeGridArray.length>0)&&(gt=!0):(gt=!0,Te.__version=k.version);let On=Te.currentProgram;gt===!0&&(On=co(k,N,z),F&&k.isNodeMaterial&&F.onUpdateProgram(k,On,Te));let di=!1,Zi=!1,qs=!1,Et=On.getUniforms(),Ht=Te.uniforms;if(M.useProgram(On.program)&&(di=!0,Zi=!0,qs=!0),k.id!==q&&(q=k.id,Zi=!0),Te.needsLights){let Ut=Rm(S.state.lightProbeGridArray,z);Te.lightProbeGrid!==Ut&&(Te.lightProbeGrid=Ut,Zi=!0)}if(di||j!==w){M.buffers.depth.getReversed()&&w.reversedDepth!==!0&&(w._reversedDepth=!0,w.updateProjectionMatrix()),Et.setValue(P,"projectionMatrix",w.projectionMatrix),Et.setValue(P,"viewMatrix",w.matrixWorldInverse);let $i=Et.map.cameraPosition;$i!==void 0&&$i.setValue(P,ue.setFromMatrixPosition(w.matrixWorld)),C.logarithmicDepthBuffer&&Et.setValue(P,"logDepthBufFC",2/(Math.log(w.far+1)/Math.LN2)),(k.isMeshPhongMaterial||k.isMeshToonMaterial||k.isMeshLambertMaterial||k.isMeshBasicMaterial||k.isMeshStandardMaterial||k.isShaderMaterial)&&Et.setValue(P,"isOrthographic",w.isOrthographicCamera===!0),j!==w&&(j=w,Zi=!0,qs=!0)}if(Te.needsLights&&(pn.state.sunShadowMap.length>0&&Et.setValue(P,"sunShadowMap",pn.state.sunShadowMap,Y),pn.state.directionalShadowMap.length>0&&Et.setValue(P,"directionalShadowMap",pn.state.directionalShadowMap,Y),pn.state.spotShadowMap.length>0&&Et.setValue(P,"spotShadowMap",pn.state.spotShadowMap,Y),pn.state.pointShadowMap.length>0&&Et.setValue(P,"pointShadowMap",pn.state.pointShadowMap,Y)),z.isSkinnedMesh){Et.setOptional(P,z,"bindMatrix"),Et.setOptional(P,z,"bindMatrixInverse");let Ut=z.skeleton;Ut&&(Ut.boneTexture===null&&Ut.computeBoneTexture(),Et.setValue(P,"boneTexture",Ut.boneTexture,Y))}z.isBatchedMesh&&(Et.setOptional(P,z,"batchingTexture"),Et.setValue(P,"batchingTexture",z._matricesTexture,Y),Et.setOptional(P,z,"batchingIdTexture"),Et.setValue(P,"batchingIdTexture",z._indirectTexture,Y),Et.setOptional(P,z,"batchingColorTexture"),z._colorsTexture!==null&&Et.setValue(P,"batchingColorTexture",z._colorsTexture,Y));let Ji=H.morphAttributes;if((Ji.position!==void 0||Ji.normal!==void 0||Ji.color!==void 0)&&U.update(z,H,On),(Zi||Te.receiveShadow!==z.receiveShadow)&&(Te.receiveShadow=z.receiveShadow,Et.setValue(P,"receiveShadow",z.receiveShadow)),(k.isMeshStandardMaterial||k.isMeshLambertMaterial||k.isMeshPhongMaterial)&&k.envMap===null&&N.environment!==null&&(Ht.envMapIntensity.value=N.environmentIntensity),Ht.dfgLUT!==void 0&&(Ht.dfgLUT.value=Qv()),Zi){if(Et.setValue(P,"toneMappingExposure",I.toneMappingExposure),Te.needsLights&&Pm(Ht,qs),ve&&k.fog===!0&&De.refreshFogUniforms(Ht,ve),De.refreshMaterialUniforms(Ht,k,Q,Z,S.state.transmissionRenderTarget[w.id]),Te.needsLights&&Te.lightProbeGrid){let Ut=Te.lightProbeGrid;Ht.probesSH.value=Ut.texture,Ht.probesMin.value.copy(Ut.boundingBox.min),Ht.probesMax.value.copy(Ut.boundingBox.max),Ht.probesResolution.value.copy(Ut.resolution)}Br.upload(P,yd(Te),Ht,Y)}if(k.isShaderMaterial&&k.uniformsNeedUpdate===!0&&(Br.upload(P,yd(Te),Ht,Y),k.uniformsNeedUpdate=!1),k.isSpriteMaterial&&Et.setValue(P,"center",z.center),Et.setValue(P,"modelViewMatrix",z.modelViewMatrix),Et.setValue(P,"normalMatrix",z.normalMatrix),Et.setValue(P,"modelMatrix",z.matrixWorld),k.uniformsGroups!==void 0){let Ut=k.uniformsGroups;for(let $i=0,Ys=Ut.length;$i<Ys;$i++){let Sd=Ut[$i];ie.update(Sd,On),ie.bind(Sd,On)}}return On}function Pm(w,N){w.ambientLightColor.needsUpdate=N,w.lightProbe.needsUpdate=N,w.sunLights.needsUpdate=N,w.sunLightShadows.needsUpdate=N,w.directionalLights.needsUpdate=N,w.directionalLightShadows.needsUpdate=N,w.pointLights.needsUpdate=N,w.pointLightShadows.needsUpdate=N,w.spotLights.needsUpdate=N,w.spotLightShadows.needsUpdate=N,w.rectAreaLights.needsUpdate=N,w.hemisphereLights.needsUpdate=N}function Lm(w){return w.isMeshLambertMaterial||w.isMeshToonMaterial||w.isMeshPhongMaterial||w.isMeshStandardMaterial||w.isShadowMaterial||w.isShaderMaterial&&w.lights===!0}this.getActiveCubeFace=function(){return X},this.getActiveMipmapLevel=function(){return W},this.getRenderTarget=function(){return re},this.setRenderTargetTextures=function(w,N,H){let k=G.get(w);k.__autoAllocateDepthBuffer=w.resolveDepthBuffer===!1,k.__autoAllocateDepthBuffer===!1&&(k.__useRenderToTexture=!1),G.get(w.texture).__webglTexture=N,G.get(w.depthTexture).__webglTexture=k.__autoAllocateDepthBuffer?void 0:H,k.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(w,N){let H=G.get(w);H.__webglFramebuffer=N,H.__useDefaultFramebuffer=N===void 0},this.setRenderTarget=function(w,N=0,H=0){re=w,X=N,W=H;let k=null,z=!1,ve=!1;if(w){let ye=G.get(w);if(ye.__useDefaultFramebuffer!==void 0){M.bindFramebuffer(P.FRAMEBUFFER,ye.__webglFramebuffer),te.copy(w.viewport),Ne.copy(w.scissor),Ae=w.scissorTest,M.viewport(te),M.scissor(Ne),M.setScissorTest(Ae),q=-1;return}else if(ye.__webglFramebuffer===void 0)Y.setupRenderTarget(w);else if(ye.__hasExternalTextures)Y.rebindTextures(w,G.get(w.texture).__webglTexture,G.get(w.depthTexture).__webglTexture);else if(w.depthBuffer){let rt=w.depthTexture;if(ye.__boundDepthTexture!==rt){if(rt!==null&&G.has(rt)&&(w.width!==rt.image.width||w.height!==rt.image.height))throw new Error("THREE.WebGLRenderer: Attached DepthTexture is initialized to the incorrect size.");Y.setupDepthRenderbuffer(w)}}let Ce=w.texture;(Ce.isData3DTexture||Ce.isDataArrayTexture||Ce.isCompressedArrayTexture)&&(ve=!0);let Pe=G.get(w).__webglFramebuffer;w.isWebGLCubeRenderTarget?(Array.isArray(Pe[N])?k=Pe[N][H]:k=Pe[N],z=!0):w.samples>0&&Y.useMultisampledRTT(w)===!1?k=G.get(w).__webglMultisampledFramebuffer:Array.isArray(Pe)?k=Pe[H]:k=Pe,te.copy(w.viewport),Ne.copy(w.scissor),Ae=w.scissorTest}else te.copy(be).multiplyScalar(Q).floor(),Ne.copy(Xe).multiplyScalar(Q).floor(),Ae=Tt;if(H!==0&&(k=V),M.bindFramebuffer(P.FRAMEBUFFER,k)&&M.drawBuffers(w,k),M.viewport(te),M.scissor(Ne),M.setScissorTest(Ae),z){let ye=G.get(w.texture);P.framebufferTexture2D(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_CUBE_MAP_POSITIVE_X+N,ye.__webglTexture,H)}else if(ve){let ye=N;for(let Ce=0;Ce<w.textures.length;Ce++){let Pe=G.get(w.textures[Ce]);P.framebufferTextureLayer(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0+Ce,Pe.__webglTexture,H,ye)}}else if(w!==null&&H!==0){let ye=G.get(w.texture);P.framebufferTexture2D(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_2D,ye.__webglTexture,H)}q=-1};function Md(w){let N=G.get(w);return(N.__readFormat!==w.format||N.__readType!==w.type)&&(N.__readFormat=w.format,N.__readType=w.type,N.__formatReadable=C.textureFormatReadable(w.format),N.__typeReadable=C.textureTypeReadable(w.type)),N}this.readRenderTargetPixels=function(w,N,H,k,z,ve,we,ye=0){if(!(w&&w.isWebGLRenderTarget)){He("WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Ce=G.get(w).__webglFramebuffer;if(w.isWebGLCubeRenderTarget&&we!==void 0&&(Ce=Ce[we]),Ce){M.bindFramebuffer(P.FRAMEBUFFER,Ce);try{let Pe=w.textures[ye],rt=Pe.format,ut=Pe.type;w.textures.length>1&&P.readBuffer(P.COLOR_ATTACHMENT0+ye);let Re=Md(Pe);if(Re.__formatReadable===!1){He("WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(Re.__typeReadable===!1){He("WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}N>=0&&N<=w.width-k&&H>=0&&H<=w.height-z&&P.readPixels(N,H,k,z,me.convert(rt),me.convert(ut),ve)}finally{let Pe=re!==null?G.get(re).__webglFramebuffer:null;M.bindFramebuffer(P.FRAMEBUFFER,Pe)}}},this.readRenderTargetPixelsAsync=async function(w,N,H,k,z,ve,we,ye=0){if(!(w&&w.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let Ce=G.get(w).__webglFramebuffer;if(w.isWebGLCubeRenderTarget&&we!==void 0&&(Ce=Ce[we]),Ce)if(N>=0&&N<=w.width-k&&H>=0&&H<=w.height-z){M.bindFramebuffer(P.FRAMEBUFFER,Ce);let Pe=w.textures[ye],rt=Pe.format,ut=Pe.type;w.textures.length>1&&P.readBuffer(P.COLOR_ATTACHMENT0+ye);let Re=Md(Pe);if(Re.__formatReadable===!1)throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(Re.__typeReadable===!1)throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");let bt=P.createBuffer();P.bindBuffer(P.PIXEL_PACK_BUFFER,bt),P.bufferData(P.PIXEL_PACK_BUFFER,ve.byteLength,P.STREAM_READ),P.readPixels(N,H,k,z,me.convert(rt),me.convert(ut),0),P.bindBuffer(P.PIXEL_PACK_BUFFER,null);let Kt=re!==null?G.get(re).__webglFramebuffer:null;M.bindFramebuffer(P.FRAMEBUFFER,Kt);let Ot=P.fenceSync(P.SYNC_GPU_COMMANDS_COMPLETE,0);return P.flush(),await $f(P,Ot,4),P.bindBuffer(P.PIXEL_PACK_BUFFER,bt),P.getBufferSubData(P.PIXEL_PACK_BUFFER,0,ve),P.bindBuffer(P.PIXEL_PACK_BUFFER,null),P.deleteBuffer(bt),P.deleteSync(Ot),ve}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(w,N=null,H=0){let k=Math.pow(2,-H),z=Math.floor(w.image.width*k),ve=Math.floor(w.image.height*k),we=N!==null?N.x:0,ye=N!==null?N.y:0;Y.setTexture2D(w,0),P.copyTexSubImage2D(P.TEXTURE_2D,H,0,0,we,ye,z,ve),M.unbindTexture()},this.copyTextureToTexture=function(w,N,H=null,k=null,z=0,ve=0){let we,ye,Ce,Pe,rt,ut,Re,bt,Kt,Ot=w.isCompressedTexture?w.mipmaps[ve]:w.image;if(H!==null)we=H.max.x-H.min.x,ye=H.max.y-H.min.y,Ce=H.isBox3?H.max.z-H.min.z:1,Pe=H.min.x,rt=H.min.y,ut=H.isBox3?H.min.z:0;else{let Ht=Math.pow(2,-z);we=Math.floor(Ot.width*Ht),ye=Math.floor(Ot.height*Ht),w.isDataArrayTexture?Ce=Ot.depth:w.isData3DTexture?Ce=Math.floor(Ot.depth*Ht):Ce=1,Pe=0,rt=0,ut=0}k!==null?(Re=k.x,bt=k.y,Kt=k.z):(Re=0,bt=0,Kt=0);let Pt=me.convert(N.format),ln=me.convert(N.type),Te;N.isData3DTexture?(Y.setTexture3D(N,0),Te=P.TEXTURE_3D):N.isDataArrayTexture||N.isCompressedArrayTexture?(Y.setTexture2DArray(N,0),Te=P.TEXTURE_2D_ARRAY):(Y.setTexture2D(N,0),Te=P.TEXTURE_2D),M.activeTexture(P.TEXTURE0),M.pixelStorei(P.UNPACK_FLIP_Y_WEBGL,N.flipY),M.pixelStorei(P.UNPACK_PREMULTIPLY_ALPHA_WEBGL,N.premultiplyAlpha),M.pixelStorei(P.UNPACK_ALIGNMENT,N.unpackAlignment);let pn=M.getParameter(P.UNPACK_ROW_LENGTH),gt=M.getParameter(P.UNPACK_IMAGE_HEIGHT),On=M.getParameter(P.UNPACK_SKIP_PIXELS),di=M.getParameter(P.UNPACK_SKIP_ROWS),Zi=M.getParameter(P.UNPACK_SKIP_IMAGES);M.pixelStorei(P.UNPACK_ROW_LENGTH,Ot.width),M.pixelStorei(P.UNPACK_IMAGE_HEIGHT,Ot.height),M.pixelStorei(P.UNPACK_SKIP_PIXELS,Pe),M.pixelStorei(P.UNPACK_SKIP_ROWS,rt),M.pixelStorei(P.UNPACK_SKIP_IMAGES,ut);let qs=w.isDataArrayTexture||w.isData3DTexture,Et=N.isDataArrayTexture||N.isData3DTexture;if(w.isDepthTexture){let Ht=G.get(w),Ji=G.get(N),Ut=G.get(Ht.__renderTarget),$i=G.get(Ji.__renderTarget);M.bindFramebuffer(P.READ_FRAMEBUFFER,Ut.__webglFramebuffer),M.bindFramebuffer(P.DRAW_FRAMEBUFFER,$i.__webglFramebuffer);for(let Ys=0;Ys<Ce;Ys++)qs&&(P.framebufferTextureLayer(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,G.get(w).__webglTexture,z,ut+Ys),P.framebufferTextureLayer(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,G.get(N).__webglTexture,ve,Kt+Ys)),P.blitFramebuffer(Pe,rt,we,ye,Re,bt,we,ye,P.DEPTH_BUFFER_BIT,P.NEAREST);M.bindFramebuffer(P.READ_FRAMEBUFFER,null),M.bindFramebuffer(P.DRAW_FRAMEBUFFER,null)}else if(z!==0||w.isRenderTargetTexture||G.has(w)){let Ht=G.get(w),Ji=G.get(N);M.bindFramebuffer(P.READ_FRAMEBUFFER,D),M.bindFramebuffer(P.DRAW_FRAMEBUFFER,B);for(let Ut=0;Ut<Ce;Ut++)qs?P.framebufferTextureLayer(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,Ht.__webglTexture,z,ut+Ut):P.framebufferTexture2D(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_2D,Ht.__webglTexture,z),Et?P.framebufferTextureLayer(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,Ji.__webglTexture,ve,Kt+Ut):P.framebufferTexture2D(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_2D,Ji.__webglTexture,ve),z!==0?P.blitFramebuffer(Pe,rt,we,ye,Re,bt,we,ye,P.COLOR_BUFFER_BIT,P.NEAREST):Et?P.copyTexSubImage3D(Te,ve,Re,bt,Kt+Ut,Pe,rt,we,ye):P.copyTexSubImage2D(Te,ve,Re,bt,Pe,rt,we,ye);M.bindFramebuffer(P.READ_FRAMEBUFFER,null),M.bindFramebuffer(P.DRAW_FRAMEBUFFER,null)}else Et?w.isDataTexture||w.isData3DTexture?P.texSubImage3D(Te,ve,Re,bt,Kt,we,ye,Ce,Pt,ln,Ot.data):N.isCompressedArrayTexture?P.compressedTexSubImage3D(Te,ve,Re,bt,Kt,we,ye,Ce,Pt,Ot.data):P.texSubImage3D(Te,ve,Re,bt,Kt,we,ye,Ce,Pt,ln,Ot):w.isDataTexture?P.texSubImage2D(P.TEXTURE_2D,ve,Re,bt,we,ye,Pt,ln,Ot.data):w.isCompressedTexture?P.compressedTexSubImage2D(P.TEXTURE_2D,ve,Re,bt,Ot.width,Ot.height,Pt,Ot.data):P.texSubImage2D(P.TEXTURE_2D,ve,Re,bt,we,ye,Pt,ln,Ot);M.pixelStorei(P.UNPACK_ROW_LENGTH,pn),M.pixelStorei(P.UNPACK_IMAGE_HEIGHT,gt),M.pixelStorei(P.UNPACK_SKIP_PIXELS,On),M.pixelStorei(P.UNPACK_SKIP_ROWS,di),M.pixelStorei(P.UNPACK_SKIP_IMAGES,Zi),ve===0&&N.generateMipmaps&&P.generateMipmap(Te),M.unbindTexture()},this.initRenderTarget=function(w){G.get(w).__webglFramebuffer===void 0&&Y.setupRenderTarget(w)},this.initTexture=function(w){w.isCubeTexture?Y.setTextureCube(w,0):w.isData3DTexture?Y.setTexture3D(w,0):w.isDataArrayTexture||w.isCompressedArrayTexture?Y.setTexture2DArray(w,0):Y.setTexture2D(w,0),M.unbindTexture()},this.resetState=function(){X=0,W=0,re=null,M.reset(),Se.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return ni}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;let t=this.getContext();t.drawingBufferColorSpace=it._getDrawingBufferColorSpace(e),t.unpackColorSpace=it._getUnpackColorSpace()}};var sn=(s,e,t)=>{let n=Math.max(0,Math.min(1,(s-e)/(t-e)));return n*n*(3-2*n)};function eM(s,{reduced:e=!1}={}){let t=Math.max(0,Number.isFinite(s)?s:0),n=e?5:15;return e?{time:t,duration:n,done:t>=n,chapter:"\u65B0\u5883",scene:!0,hand:0,release:1,lift:1,bloom:1,darken:1,reveal:1,pull:1,flash:0,title:sn(t,.4,1.3),feathers:0,still:!1,crack:1,push:1,beacon:1,suspense:0}:{time:t,duration:n,done:t>=n,chapter:t<1.5?"\u4E07\u7C41\u4FF1\u5BC2":t<4.6?"\u638C\u8D77 \xB7 \u5929\u88C2":t<8.5?"\u4E00\u638C\u5F00\u5929":t<11.8?"\u8BF8\u5929\u4E4B\u5916":"\u638C\u5929\u8BC0",scene:t>=1.5,still:t<1.5,hand:1-sn(t,6.3,7.8),lift:sn(t,1.5,4.2),crack:sn(t,2.1,4.5),push:sn(t,4.6,5.05),release:sn(t,4.6,7.4),reveal:sn(t,1.5,2.1),pull:sn(t,5,9.2),bloom:sn(t,4.6,6),darken:sn(t,11.4,12.9),flash:.42*sn(t,4.6,4.75)*(1-sn(t,4.75,5.12)),title:sn(t,12.3,13.6),feathers:sn(t,2.2,4.2)*(1-sn(t,8.3,10)),beacon:sn(t,9.2,9.8),suspense:sn(t,9.7,10.3)*(1-sn(t,11.8,12.4))}}var xc=class{constructor(){this.reset()}reset(){this.active=!1,this.time=0,this.reduced=!1,this.cues=new Set}start(e=!1){this.reset(),this.active=!0,this.reduced=e}tick(e,t=!1){return this.active&&!t&&(this.time=Math.min(this.reduced?5:15,this.time+Math.max(0,Math.min(.05,Number.isFinite(e)?e:0)))),this.frame}skip(){this.active&&(this.time=this.reduced?5:15)}get frame(){return eM(this.time,{reduced:this.reduced})}takeCues(){if(!this.active)return[];let e=[];for(let[t,n]of this.reduced?[["heavens",.4]]:[["heartbeat",.25],["fracture",2.1],["skybreak",4.6],["soar",7.2],["beacon",9.4],["heavens",12.3]])this.time>=n&&!this.cues.has(t)&&(this.cues.add(t),this.frame.done||e.push(t));return e}};var Su=Math.PI*2,ps=(s=0,e=0,t=0)=>new R(s,e,t),li=(s=>()=>(s=1664525*s+1013904223>>>0,s/4294967296))(8127);function tM(){let s=document.createElement("canvas");s.width=512,s.height=256;let e=s.getContext("2d");for(let t=0;t<55;t++){let n=80+li()*350,i=90+li()*85,r=24+li()*56,a=e.createRadialGradient(n,i,0,n,i,r);a.addColorStop(0,"rgba(222,237,247,.16)"),a.addColorStop(.45,"rgba(185,211,229,.08)"),a.addColorStop(1,"rgba(160,190,219,0)"),e.fillStyle=a,e.fillRect(n-r,i-r,r*2,r*2)}return new Mi(s)}var _c=class{constructor(e){this.world=e,this.clock=new xc,this.scene=new ss,this.scene.fog=new ha(10204610,.0018),this.camera=new zt(49,1,.1,650),this.built=!1,this.materials=[],this.featherParts=[]}async init(){[this.backdrop,this.heaven]=await Promise.all([this.world.texture("ending-cloudsea.jpg"),this.world.texture("ending-heaven.jpg")]),this.heaven&&(this.heaven.colorSpace=Ct,this.heaven.wrapS=this.heaven.wrapT=rn),this.backdrop&&(this.backdrop.colorSpace=Ct,this.backdrop.wrapS=this.backdrop.wrapT=rn)}restoreBand(){this.world.bandShell.visible=!0;for(let e of this.world.bandPieces)e.mesh.position.copy(e.p),e.mesh.quaternion.copy(e.q)}start(){this.restoreBand(),this.clock.start(window.matchMedia("(prefers-reduced-motion: reduce)").matches),this.built||this.build(),this.world.handRig.scale.setScalar(.82),this.world.handRig.rotation.y=0}reset(){this.restoreBand(),this.clock.reset(),this.world.handRig.visible=!0,this.world.handRig.scale.setScalar(.82),this.world.handRig.rotation.y=0}skip(){this.clock.skip()}build(){let e=this.world;this.built=!0,this.scene.add(new hs(12904447,2505025,2.4));let t=new Nn(16768157,4);t.position.set(-35,55,8),this.scene.add(t);let n=new Nn(8239325,2.5);n.position.set(20,15,-35),this.scene.add(n);let i=new Ee(new Nt(450,40,24),new Bt({side:qt,depthWrite:!1,uniforms:{},vertexShader:"varying vec3 vP;void main(){vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",fragmentShader:`varying vec3 vP;
   void main(){vec3 d=normalize(vP);float h=clamp(d.y*.85+.18,0.,1.);vec3 c=mix(vec3(.65,.73,.72),vec3(.045,.13,.23),pow(h,.6));vec3 s=normalize(vec3(-.28,.25,-.9));float a=acos(clamp(dot(d,s),-1.,1.));c+=vec3(1.,.69,.28)*(.18*exp(-a*3.)+.6*exp(-a*21.)+.85*(1.-smoothstep(.043,.048,a)));gl_FragColor=vec4(c,1.);}`}));if(this.backdrop){this.skyUniforms={map:{value:this.backdrop},heaven:{value:this.heaven||this.backdrop},crack:{value:0},opening:{value:0},beacon:{value:0},time:{value:0},aspect:{value:1},travel:{value:0}};let h=new Bt({depthTest:!1,depthWrite:!1,uniforms:this.skyUniforms,vertexShader:"varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,1.,1.);}",fragmentShader:`uniform sampler2D map;uniform sampler2D heaven;uniform float time;uniform float aspect;uniform float travel;uniform float crack;uniform float opening;uniform float beacon;varying vec2 vUv;
     float noise(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
     void main(){vec2 uv=vUv;float source=1672./941.;if(aspect<source)uv.x=(uv.x-.5)*aspect/source+.5;else uv.y=(uv.y-.5)*source/aspect+.5;
      vec2 realm=(uv-vec2(.5,.58))*(1.-travel*.15)+vec2(.5,.58);
      float cloud=1.-smoothstep(.25,.55,realm.y);realm.x+=cloud*sin(realm.y*19.+time*.55)*.007;realm.y+=cloud*sin(realm.x*14.+time*.5)*.006;
      vec3 bright=texture2D(heaven,clamp(realm,.002,.998)).rgb;
      vec2 old=uv;old.x+=sign(uv.x-.5)*opening*.22;old.y+=sin(uv.x*12.+time*.2)*.012;
      vec3 storm=texture2D(map,clamp(old,.002,.998)).rgb*vec3(.12,.19,.29);
      float center=.5+sin(vUv.y*19.)*.009+sin(vUv.y*51.)*.003;
      float width=opening*.82;float dist=abs(vUv.x-center);
      float edge=dist-width;
      float revealed=1.-smoothstep(-.004,.008,edge);
      float height=1.-smoothstep(crack*.92,crack*.92+.06,abs(vUv.y-.48));
      revealed*=height*crack;
      vec3 color=mix(storm,bright,revealed);
      float seam=exp(-abs(edge)*450.)*height*crack*(1.-smoothstep(.65,1.,opening));
      color+=vec3(2.5,1.15,.25)*seam;
      float branch=abs(abs(vUv.x-center)-(.04*sin(vUv.y*13.)+.018));
      color+=vec3(.65,.31,.08)*exp(-branch*600.)*crack*(1.-opening)*height*.5;
      vec2 lamp=realm-vec2(.5,.635);float d=length(lamp*vec2(1.,.6));color+=vec3(2.6,1.1,.22)*exp(-d*190.)*beacon;
      gl_FragColor=vec4(color,1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
     }`}),u=new Ee(new Rt(2,2),h);u.frustumCulled=!1,u.renderOrder=-100,this.scene.add(u),i.geometry.dispose(),i.material.dispose()}else this.scene.add(i);this.currents=[];for(let h=0;h<7;h++){let u=[];for(let v=0;v<=100;v++){let f=v/100,m=f*Su*1.05+h*Su/7,_=(1-f)*12+1.3;u.push(ps(Math.cos(m)*_,-9+f*48,Math.sin(m)*_-12))}let d=new Pn(u),p=new Bt({uniforms:{time:{value:0},strength:{value:0},phase:{value:h*.137}},transparent:!0,depthWrite:!1,blending:dt,toneMapped:!1,vertexShader:"varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",fragmentShader:"uniform float time;uniform float strength;uniform float phase;varying vec2 vUv;void main(){float head=fract(time*.32+phase);float trail=mod(head-vUv.x+1.,1.);float glow=exp(-trail*22.);gl_FragColor=vec4(vec3(1.,.71,.28)*(1.+glow*2.),strength*(.04+glow*.96));}"}),g=new Ee(new Wn(d,100,h%2?.035:.065,5,!1),p);this.scene.add(g),this.currents.push(g)}this.halo=new Ke,this.halo.position.set(0,37,-12),this.scene.add(this.halo);for(let h=0;h<3;h++){let u=new Ee(new ki(3+h*1.3,3.025+h*1.3,160),new Ye({color:16768926,transparent:!0,opacity:0,depthWrite:!1,blending:dt,toneMapped:!1,side:st}));this.halo.add(u)}this.sun=new Cn(new vn({map:e.glow,color:16768946,transparent:!0,opacity:0,depthWrite:!1,blending:dt,toneMapped:!1})),this.sun.position.copy(this.halo.position),this.sun.scale.set(34,34,1),this.scene.add(this.sun);let r=tM();this.clouds=[];for(let h=0;h<48;h++){let u=new Cn(new vn({map:r,color:h%3?12112865:16768941,transparent:!0,opacity:.54,depthWrite:!1,fog:!0})),d=h*2.399,p=h<10?12+li()*17:35+li()*150;u.position.set(h<10?(h%2?1:-1)*(10+h*2):Math.cos(d)*p,h<10?1+h*.6:-4+li()*5,h<10?16-h*3:Math.sin(d)*p),u.scale.set(55+li()*55,14+li()*15,1),this.scene.add(u),this.clouds.push({sprite:u,x:u.position.x,y:u.position.y,z:u.position.z,phase:h})}this.rings=[];for(let h=0;h<3;h++){let u=new Ee(new Rt(1,1),new Ye({map:e.runes,color:15976844,transparent:!0,opacity:.25,depthWrite:!1,side:st,blending:dt,toneMapped:!1}));u.rotation.x=-Math.PI/2,u.position.y=-1+h*1.8,u.scale.setScalar(45+h*21),this.scene.add(u),this.rings.push(u)}let a=new tt;a.setAttribute("position",new Oe([0,.6,0,-.12,.05,.025,0,-.35,0,.12,.05,.025],3)),a.setIndex([0,1,2,0,2,3]),a.computeVertexNormals(),this.feathers=new un(a,new Ye({color:16770216,side:st,toneMapped:!1,transparent:!0,opacity:.85}),180),this.feathers.instanceMatrix.setUsage(Qh),this.feathers.frustumCulled=!1,this.scene.add(this.feathers),this.dummy=new ft,this.sparks=new Gn(new tt,new Rn({map:e.glow,color:16766096,size:.4,transparent:!0,opacity:.6,depthWrite:!1,blending:dt}));let o=new Float32Array(300*3);for(let h=0;h<300;h++)o[h*3]=(li()-.5)*100,o[h*3+1]=li()*60,o[h*3+2]=(li()-.5)*70;this.sparks.geometry.setAttribute("position",new Ft(o,3)),this.scene.add(this.sparks),this.burst=new Ke,e.viewCamera.add(this.burst),this.burstRays=[];for(let h=0;h<48;h++){let u=new Ee(new Rt(.002,1),new Ye({color:16765835,transparent:!0,opacity:0,depthWrite:!1,blending:dt,toneMapped:!1,side:st}));this.burst.add(u),this.burstRays.push(u)}let c=new tt().setFromPoints([ps(),ps(),ps()]);this.tether=new ii(c,new zn({color:16768141,transparent:!0,opacity:0,depthWrite:!1,blending:dt,toneMapped:!1})),e.viewCamera.add(this.tether),this.tether.frustumCulled=!1;let l=this.foreground=new Ke;e.viewCamera.add(l);for(let h=0;h<72;h++){let u=new Ee(a,new Ye({color:16770216,side:st,transparent:!0,opacity:0,depthWrite:!1,toneMapped:!1}));l.add(u),this.featherParts.push(u)}l.visible=!1}update(e,t){let n=this.clock.tick(e,t);if(!this.clock.active){this.foreground&&(this.foreground.visible=!1),this.burst&&(this.burst.visible=!1),this.tether&&(this.tether.visible=!1);return}let i=this.world,r=this.clock.reduced?15:n.time,a=Math.min(1,i.viewCamera.aspect/1.3);i.handRig.position.set((.25-n.lift*.11-n.push*.07)*a,-.3+n.lift*.12-n.push*.045-(1-n.hand)*.8,-.65+n.lift*.045-n.push*.24),i.handRig.rotation.set(-n.lift*.12-n.push*.12,0,.07-n.lift*.13-n.push*.12),i.handRig.scale.setScalar(.82),i.handLight.color.set(16768927),i.handLight.intensity=(1+n.lift*3)*n.hand,i.braceletMaterial.emissiveIntensity=3+n.lift*4,i.handRig.visible=n.hand>0,this.foreground.visible=n.hand>0,i.handRig.updateMatrix(),this.palm=ps(-.015,.23,-.01).applyMatrix4(i.handRig.matrix),this.tether.visible=n.scene&&n.hand>0;let o=ps(-.025,.38,0).applyMatrix4(i.handRig.matrix),c=ps(0,.12,-1.4),l=o.clone().lerp(c,.5);l.x+=Math.sin(r*9)*.008*n.crack;let h=this.tether.geometry.attributes.position;[o,l,c].forEach((f,m)=>h.setXYZ(m,f.x,f.y,f.z)),h.needsUpdate=!0,this.tether.material.opacity=n.crack*(1-n.push)*.9,this.burst.visible=!this.clock.reduced&&n.push>0&&r<6.3;let u=kt.clamp((r-4.6)/1.5,0,1);if(this.burstRays.forEach((f,m)=>{let _=m*Su/48,b=.03+u*(.6+m%5*.06);f.position.set(Math.cos(_)*b,Math.sin(_)*b,-.85),f.rotation.z=_-Math.PI/2,f.scale.y=.04+u*.27,f.material.opacity=(1-u)*n.push*.65}),this.featherParts.forEach((f,m)=>{let _=Math.max(0,r-2.4-m*.018),b=(_*.55+m*.137)%1,x=m*2.399+r*.65,T=.012+b*b*.15;f.position.copy(this.palm).add(ps(Math.cos(x)*T,b*.8,-b*.7+Math.sin(x)*T*.25)),f.rotation.set(r+m,x,m*.6),f.scale.setScalar((.015+m%4*.005)*(1-b*.65)),f.material.opacity=_>0?n.feathers*(1-b)*.85:0}),!n.scene)return;this.skyUniforms&&(this.skyUniforms.time.value=r,this.skyUniforms.aspect.value=i.camera.aspect,this.skyUniforms.travel.value=n.pull,this.skyUniforms.crack.value=n.crack,this.skyUniforms.opening.value=n.release,this.skyUniforms.beacon.value=n.beacon),this.camera.aspect=i.camera.aspect,this.camera.updateProjectionMatrix();let d=Math.max(1,1.4/this.camera.aspect),p=n.pull;this.camera.position.set(Math.sin(n.release*.6)*4*d,12+n.pull*13,(56-n.pull*30)*d),this.camera.lookAt(0,19+n.pull*12,-12);let g=n.release,v=1-n.darken;this.currents.forEach((f,m)=>{f.material.uniforms.time.value=r,f.material.uniforms.strength.value=g*v,f.scale.setScalar(.8+g*.2),f.geometry.setDrawRange(0,Math.floor(f.geometry.index.count*g/3)*3)}),this.halo.children.forEach((f,m)=>{f.material.opacity=(.08+m*.025)*g*v,f.scale.setScalar(1+n.bloom*(.7+m*.1))}),this.halo.lookAt(this.camera.position),this.sun.material.opacity=(.025+n.bloom*.07)*g*v,this.clouds.forEach(({sprite:f,x:m,y:_,z:b,phase:x})=>{f.position.set(m+Math.sign(m||1)*n.release*48+Math.sin(r*.22+x)*5,_+Math.sin(r*.3+x)*1.8,b+n.pull*28),f.material.opacity=(.16+n.release*.38)*(1-n.darken)}),this.rings.forEach((f,m)=>{f.rotation.z=r*(m%2?-.025:.02),f.material.opacity=(.16+m*.015)*n.reveal});for(let f=0;f<180;f++){let m=(f*.61+r*(2+f%4*.35))%55-9,_=f*2.399+r*.35,b=(1-(m+9)/55)*13+1.5;this.dummy.position.set(Math.cos(_)*b,m,Math.sin(_)*b-12),this.dummy.rotation.set(r*.5+f,_,r*.7+f),this.dummy.scale.setScalar(.18+f%4*.07),this.dummy.updateMatrix(),this.feathers.setMatrixAt(f,this.dummy.matrix)}this.feathers.instanceMatrix.needsUpdate=!0,this.feathers.material.opacity=n.release*(.75-n.pull*.3)}render(){let e=this.world,t=e.composer.passes[0];t.scene=this.scene,t.camera=this.camera,e.renderer.toneMappingExposure=1.05;try{e.composer.render(),this.clock.frame.hand>0&&(e.renderer.autoClear=!1,e.renderer.clearDepth(),e.renderer.render(e.viewScene,e.viewCamera),e.renderer.autoClear=!0)}finally{t.scene=e.scene,t.camera=e.camera}}get diagnostics(){return{active:this.clock.active,handVisible:this.world.handRig.visible,handPosition:this.world.handRig.position.toArray(),palm:this.palm?.toArray(),cloudPosition:this.clouds?.[0].sprite.position.toArray(),skyTime:this.skyUniforms?.time.value,riftOpening:this.skyUniforms?.opening.value,beaconLight:this.skyUniforms?.beacon.value,heavenLoaded:!!this.heaven,handYaw:this.world.handRig.rotation.y,bandRestored:this.world.bandShell.visible&&this.world.bandPieces.every(e=>e.mesh.position.distanceTo(e.p)<1e-4),...this.clock.frame,lightCurrents:this.currents?.length||0,camera:this.camera.position.toArray()}}};function nM(s,e,t,n){return s.area>0?1:s.phase!=="travel"?0:kt.smoothstep((e-t)/n,.12,.82)}async function Up(s){let e=await s.texture("sky-night.jpg");if(e){e.wrapT=rn;let t=new Nt(285,64,48),n=t.attributes.uv;for(let r=0;r<n.count;r++)n.setX(r,.5+.5*Math.tanh((n.getX(r)-.5)*6)/Math.tanh(3)),n.setY(r,Math.min(1,.16+1.1*Math.tanh(Math.max(0,n.getY(r)-.5)*4)));n.needsUpdate=!0;let i=new Ye({color:9285848,map:e,side:qt,fog:!1,toneMapped:!1,transparent:!0,depthWrite:!1});s.nightDome=new Ee(t,i),s.nightDome.rotation.y=1.85,s.nightDome.position.y=25,s.nightDome.renderOrder=-999,s.scene.add(s.nightDome)}s.courtLights=[];for(let[t,n,i,r,a]of[[-8,3,-18,65,26],[8,3,-18,65,26],[0,4,-23,65,22]]){let o=new Ln(16750127,r,a,2);o.position.set(t,n,i),s.scene.add(o),s.courtLights.push(o)}s.reflections=new Ke,s.scene.add(s.reflections);for(let t of[-12,12])for(let n of[-19,-7,5,17]){let i=new Ee(new Rt(2.8,9),new Ye({map:s.glow,color:16751414,opacity:.13,transparent:!0,blending:dt,depthWrite:!1}));i.rotation.x=-Math.PI/2,i.position.set(t,-.025,n+1),s.reflections.add(i)}s.daylight=0}function Fp(s,e){let t=nM(e,s.time,s.travelStart,s.travelDuration);s.daylight=t,s.nightDome&&(s.nightDome.visible=t<1,s.nightDome.material.opacity=1-t),s.skyMaterial&&e.area===0&&(s.skyMaterial.opacity=t);let n=new Me(464173),i=new Me(4281693);e.area===0&&s.scene.fog.color.copy(n).lerp(i,t),s.hemi.color.set(8236280).lerp(new Me(11916519),t),s.hemi.intensity=.75+t*1.35,s.sun.color.set(10206463).lerp(new Me(16767138),t),s.sun.intensity=1.35+t*2.15,s.fill.intensity=.48+t*.52,s.scene.environmentIntensity=.14+t*.21;for(let r of s.courtLights)r.intensity=(1-t)*65+t*8;s.reflections.visible=e.area===0,s.reflections.children.forEach(r=>r.material.opacity=.16*(1-t)),s.materials.floor.roughness=.32+t*.23,s.handKey.color.set(16768442).lerp(new Me(16768444),t),s.handKey.intensity=2.7+t*.2,s.handFill.intensity=.9+t*.3}var yc=(s,e,t)=>new R(s,e,t);function Yi(s){s.traverse(e=>{if(e.isInstancedMesh&&e.dispose(),e.geometry?.dispose(),e.material)for(let t of Array.isArray(e.material)?e.material:[e.material])t.dispose()})}function Op(){let s=new Ke,e=new Vn;e.moveTo(0,1.3),e.lineTo(.095,.94),e.lineTo(.075,-.38),e.lineTo(-.075,-.38),e.lineTo(-.095,.94),e.closePath();let t=new nt({color:14286835,metalness:.85,roughness:.18,emissive:3378687,emissiveIntensity:2.3}),n=new Ee(new Ia(e,{depth:.035,bevelEnabled:!0,bevelSize:.018,bevelThickness:.012,bevelSegments:1,steps:1}),t);s.add(n);let i=new nt({color:13939832,metalness:.8,roughness:.28}),r=new Ee(new Mn(.43,.065,.08),i);r.position.y=-.4,s.add(r);let a=new Ee(new _n(.042,.042,.35,8),new nt({color:1653817}));return a.position.y=-.6,s.add(a),s}function vc(s,e,t){let n=[];for(let r=0;r<=18;r++){let a=r/18,o=e.clone().lerp(t,a);r&&r<18&&o.add(yc((Math.random()-.5)*.65,(Math.random()-.5)*.28,(Math.random()-.5)*.5)),n.push(o)}let i=new Ke;for(let[r,a,o]of[[.055,16747556,.5],[.018,16773581,1]]){let c=new Wn(new Pn(n,!1,"catmullrom",0),50,r,5,!1);i.add(new Ee(c,new Ye({color:a,transparent:!0,opacity:o,depthWrite:!1,blending:dt,toneMapped:!1})))}s.scene.add(i),s.spellEffects.push({root:i,age:0,life:.65,kind:"bolt"})}function bu(s,e){let t=s.camera.position.clone().add(yc(.45,-.12,-2.2).applyQuaternion(s.camera.quaternion)),n=new Ke,i=new Ee(new Rt(.2,.42),new Ye({map:s.thunderPaper,side:st,color:16768689,toneMapped:!1}));n.add(i);let r=new Ln(16753452,15,8);n.add(r),n.position.copy(t),n.quaternion.copy(s.camera.quaternion),s.scene.add(n),s.spellEffects.push({root:n,age:0,life:1.2,kind:"talisman",from:t,to:e.clone()});for(let a=0;a<5;a++){let o=a*Math.PI*2/5;vc(s,e.clone().add(yc(Math.cos(o)*2.4,8+Math.random()*2,Math.sin(o)*2.4)),e)}vc(s,t,e),s.emitParticles(e,16760404,140,8),s.ring(e,16756021,6)}function Bp(s,e){s.spellEffects=s.spellEffects.filter(t=>{t.age+=e;let n=t.age/t.life;return t.kind==="talisman"?(t.root.position.lerpVectors(t.from,t.to,Math.min(1,n*1.5)),t.root.rotateZ(e*.8)):t.root.children.forEach((i,r)=>i.material.opacity=t.kind==="wake"?(1-n)*.8:(r===0?.5:1)*(.65+.35*Math.abs(Math.sin(t.age*75)))),n>=1?(s.scene.remove(t.root),Yi(t.root),!1):!0})}function kp(s,e,t){let n=new Ke,i=t.clone().sub(e),r=new R().crossVectors(i.clone().normalize(),yc(0,1,0));for(let a=0;a<3;a++){let o=[];for(let c=0;c<=24;c++){let l=c/24,h=e.clone().lerp(t,l),u=Math.sin(l*Math.PI)*(.16+a*.07),d=l*22+a*2.1;h.addScaledVector(r,Math.cos(d)*u),h.y+=Math.sin(d)*u,o.push(h)}n.add(new Ee(new Wn(new Pn(o),64,a===0?.014:.006,5,!1),new Ye({color:a===0?8571135:2652415,transparent:!0,opacity:.75,blending:dt,depthWrite:!1,toneMapped:!1})))}s.scene.add(n),s.spellEffects.push({root:n,age:0,life:.35,kind:"wake"})}var zp={sword:6073087,guard:16760661,thunder:16752172},Mc=(s,e=1)=>new Ye({color:s,transparent:!0,opacity:e,depthWrite:!1,side:st,blending:dt,toneMapped:!1});function Gp(s){s.deathBursts=[],s.handAuras={};for(let e of Object.keys(zp)){let t=new Ke;t.visible=!1,t.position.set(-.025,e==="thunder"?.16:.27,.045),s.handRig.add(t);let n=zp[e];if(e==="guard"){let a=new Ee(new Rt(.38,.38),new Ye({map:s.runes,color:n,transparent:!0,opacity:.9,blending:dt,depthWrite:!1,side:st,toneMapped:!1}));a.position.z=-.055,a.userData.spin=!0,t.add(a);for(let o=0;o<5;o++){let c=new Ee(new Rt(.046,.115),new Ye({map:s.guardPaper,color:16767107,transparent:!0,side:st,depthWrite:!1,toneMapped:!1}));c.userData.orbit=o*Math.PI*2/5,t.add(c);let l=new Is(new va(c.geometry),new zn({color:16761954,transparent:!0,blending:dt,depthWrite:!1,toneMapped:!1}));c.add(l)}}else{let a=e==="sword"?5:12;for(let o=0;o<a;o++){let c=[];for(let h=0;h<18;h++){let u=o*Math.PI*2/a+h*.16,d=.1+h%3*.012;c.push(new R(Math.cos(u)*d,-.14+h*.017,Math.sin(u)*d+.035))}let l=new Ee(new Wn(new Pn(c),36,7e-4,4,!1),Mc(n,.85));t.add(l)}}let i=[];for(let a=0;a<65;a++){let o=a*2.399;i.push(Math.cos(o)*(.09+a%7*.014),-.17+a/65*.4,Math.sin(o)*.08+.06)}let r=new tt;r.setAttribute("position",new Oe(i,3)),t.add(new Gn(r,new Rn({map:s.glow,color:n,size:.012,transparent:!0,opacity:.8,blending:dt,depthWrite:!1,toneMapped:!1}))),t.traverse(a=>{a.material&&(a.userData.baseOpacity=a.material.opacity)}),s.handAuras[e]=t}}function Vp(s,e){s.auraCast={mode:e,start:s.time,life:{sword:.8,guard:1.15,thunder:1.25}[e]}}function Hp(s,e,t){let n=["reflection","mirror"].includes(t)?9563884:t==="dragonfly"?13611263:16760962,i=new Ke;i.position.copy(e),s.scene.add(i);let r=new Ee(new Nt(.7,12,8),Mc(16773589));i.add(r);let a=[];for(let l=0;l<2;l++){let h=new Ee(new si(1,.045,6,48),Mc(n));h.quaternion.copy(s.camera.quaternion),h.rotateX(l*.7),i.add(h),a.push(h)}let o=new un(new Hn(.16),Mc(n),36),c=[];i.add(o);for(let l=0;l<36;l++)c.push(new R(Math.sin(l*2.4),Math.cos(l*1.7),Math.sin(l*4.1)).normalize().multiplyScalar(4+l%7));s.deathBursts.push({root:i,flash:r,rings:a,shards:o,vel:c,age:0,life:1.2}),s.emitParticles(e,n,260,12)}function Wp(s,e){let t=s.auraCast,n=t?(s.time-t.start)/t.life:2;for(let[r,a]of Object.entries(s.handAuras||{})){if(a.visible=r===t?.mode&&n<1,!a.visible)continue;let o=Math.min(1,n*12)*Math.min(1,(1-n)*5);a.scale.setScalar(r==="guard"?.8+Math.sin(Math.min(1,n)*Math.PI)*.15:.64+Math.sin(Math.min(1,n)*Math.PI)*.12),a.rotation.z=r==="guard"?0:Math.sin(s.time*25)*.035;for(let c of a.children)if(c.userData.spin&&(c.rotation.z=-s.time*.4),c.userData.orbit!==void 0){let l=c.userData.orbit+s.time*.45;c.position.set(Math.cos(l)*.24,Math.sin(l)*.18,-.03),c.rotation.z=-Math.cos(l)*.2}a.traverse(c=>{c.material&&(c.material.opacity=c.userData.baseOpacity*o*(r==="thunder"?.72+.28*Math.sin(s.time*53)**2:1))})}let i=new ft;s.deathBursts=(s.deathBursts||[]).filter(r=>{r.age+=e;let a=r.age/r.life;r.flash.scale.setScalar(1+a*7),r.flash.material.opacity=Math.max(0,1-a*6);for(let[o,c]of r.rings.entries())c.scale.setScalar(.2+a*(5+o*2)),c.material.opacity=Math.max(0,1-a*1.4);for(let o=0;o<r.vel.length;o++)i.position.copy(r.vel[o]).multiplyScalar(r.age),i.position.y-=r.age*r.age*2,i.rotation.set(r.age*(o%4+2),r.age*3,o),i.scale.setScalar(Math.max(.01,1-a)),i.updateMatrix(),r.shards.setMatrixAt(o,i.matrix);return r.shards.instanceMatrix.needsUpdate=!0,r.shards.material.opacity=Math.max(0,1-a),a>=1?(r.root.removeFromParent(),Yi(r.root),!1):!0})}function Xp(s){for(let e of s.deathBursts||[])e.root.removeFromParent(),Yi(e.root);s.deathBursts=[],s.auraCast=null;for(let e of Object.values(s.handAuras||{}))e.visible=!1}var qp=.7158962795941376*Math.PI*2,Tu=425/887*Math.PI,fn={x:-288*Math.cos(qp)*Math.sin(Tu),y:25+288*Math.cos(Tu),z:288*Math.sin(qp)*Math.sin(Tu)},xt={start:-35,end:fn.z,width:1.35,safeX:.38,height:1.55,sag:6},Yp=s=>s===0?8.5:s===1?18:3.2,bc=s=>Math.max(0,Math.min(1,s)),Gs=s=>{let e=bc(s);return e*e*(3-2*e)};function Ki(s){let e=bc((s-xt.start)/(xt.end-xt.start));return xt.height+(fn.y-xt.height)*Gs(e)-xt.sag*4*e*(1-e)}function qn(s){return fn.x*Gs((s-xt.start)/(xt.end-xt.start))}function wu(s){return Math.atan((qn(s+.05)-qn(s-.05))/.1)}function eo(s,e=0,t=0){let n=wu(s);return{x:qn(s)+e*Math.cos(n),y:Ki(s)+t,z:s-e*Math.sin(n)}}function iM(s){return s>-23.6?1.55*bc((-s-18)/5.6):s>=xt.start?xt.height:Ki(s)}function Kp(s,e){let t=Gs((e-.09)/.91),n=s.z+(-43-s.z)*t,i=Gs(t/Math.max(.01,(-18-s.z)/(-43-s.z)));return{x:s.x*(1-i)+qn(n),y:1.75+iM(n),z:n}}var yt={x:fn.x,y:-24,z:fn.z-30+103},Sc={x:yt.x,y:yt.y+1.75,z:yt.z-103};function Au(s,e){let t=bc(e),n=fn;if(t<=.58){let r=Gs(t/.58),a=s.z+(xt.end-s.z)*r;return{x:qn(a)+(s.x-qn(s.z))*(1-r),y:Ki(a)+1.75,z:a}}if(t<=.73){let r=Gs((t-.58)/.15);return{x:n.x,y:n.y+1.75,z:n.z-11*r}}let i=Gs((t-.73)/.27);return{x:n.x+Math.sin(i*Math.PI)*7,y:n.y+1.75+(Sc.y-n.y-1.75)*i,z:n.z-11+(Sc.z-n.z+11)*i}}function Zp(s){let e=new Ke;e.name="original-pavilion-interior",e.position.set(fn.x,fn.y,fn.z-4.5),e.visible=!1,s.scene.add(e),s.pavilionPassage=e;let t=s.materials,n=new nt({color:3813417,roughness:.9}),i=new nt({color:10267296,map:t.stone.map,roughness:.86});s.box(i,0,-.14,0,7,.28,11,e);for(let a of[-1,1])for(let o of[-4.5,0,4.5])s.cylinder(n,.18,.25,5.8,a*2.7,2.9,o,e,12),s.box(i,a*2.7,.2,o,.65,.4,.65,e),s.box(n,0,5.5,o,6.4,.35,.35,e);s.box(n,0,5.9,0,7,.35,11,e);for(let a of[-2.7,2.7])s.box(n,a,1,0,.12,.12,8,e),s.box(n,a,.45,0,.1,.1,8,e);for(let a of[-2,2])for(let o of[-3,3])s.box(t.light,a,4.8,o,.25,.55,.25,e);let r=new Ke;s.scene.add(r),r.visible=!1,s.descentCliff=r;for(let a of[-1,1])s.mesh(new Vt(1,2),t.stone,fn.x+a*13,(fn.y+yt.y)/2,fn.z-8,8,(fn.y-yt.y)/2+5,11,r)}function Jp(s,e){let t=new Ke,n=new nt({color:9666391,metalness:.78,roughness:.4}),i=new It({color:8834001,metalness:.75,roughness:.15,transparent:!0,opacity:.88,clearcoat:1}),r=new Ye({color:16755284,toneMapped:!1}),a=(o,c,l=0,h=0,u=0,d=1,p=d,g=d)=>{let v=new Ee(o,c);return v.position.set(l,h,u),v.scale.set(d,p,g),t.add(v),v};if(["reflection","mirror"].includes(e.kind)){a(new Hn(1,0),i,0,.6,0,e.kind==="mirror"?1.2:.9,1.6,.48);for(let c=0;c<7;c++){let l=c*Math.PI*2/7,h=a(new Hn(.4,0),i,Math.cos(l)*1.7,.6+Math.sin(l)*1.7,0,.6,1.8,.3);h.rotation.z=l}let o=a(new si(1.9,.04,8,64),n,0,.6,-.1);o.rotation.y=.3,a(new Vt(.23,1),new Ye({color:13697011}),0,.7,.6)}else if(e.kind==="manta"){let o=new nt({color:2318710,roughness:.4,metalness:.55,side:st});a(new Nt(1,24,16),o,0,.5,0,.7,.35,1.7);for(let c of[-1,1]){let l=new Vn;l.moveTo(0,0),l.quadraticCurveTo(c*1.6,1.3,c*3.3,.25),l.quadraticCurveTo(c*2.1,-.5,0,-.4);let h=a(new ls(l,24),o,0,.5,0);h.rotation.x=-Math.PI/2,h.userData.flap=c}s.tube([[0,.4,-1],[0,.25,-2.3],[.5,.4,-3.4],[.9,.8,-4.6]],.05,n,t);for(let c of[-1,1])a(new Nt(.08,12,8),r,c*.25,.72,1.05)}else if(e.kind==="dragonfly"){let o=new It({color:7391157,metalness:.58,roughness:.22,clearcoat:1,iridescence:.9,iridescenceIOR:1.35}),c=new It({color:12708319,roughness:.13,metalness:.18,transparent:!0,opacity:.68,side:st,iridescence:1,depthWrite:!1});a(new Nt(1,24,16),o,0,.7,0,.38,.4,.85);for(let l=0;l<9;l++){let h=a(new Nt(1,14,10),l%3===0?n:o,0,.65-l*.035,-.7-l*.34,.22-l*.014,.2-l*.012,.28);h.userData.segment=l}a(new Nt(.42,24,16),o,0,.8,.85,1,.9,1);for(let l of[-1,1]){let h=a(new Vt(.23,2),new nt({color:10411971,emissive:5487768,emissiveIntensity:.6,roughness:.24}),l*.3,.94,1.03);h.userData.demonEye=!0;for(let u=0;u<2;u++){let d=new Ke;d.position.set(l*.16,.86,.35-u*.95),d.rotation.x=.23,d.userData.dragonWing={side:l,pair:u},t.add(d);let p=new Vn;p.moveTo(0,0),p.bezierCurveTo(l*.9,.55,l*2.8,.65,l*3.3,.08),p.bezierCurveTo(l*2.9,-.5,l*.8,-.45,0,0);let g=new Ee(new ls(p,28),c);g.rotation.x=-Math.PI/2,d.add(g);for(let v=0;v<7;v++){let f=(v+1)/8;s.tube([[0,0,0],[l*1.4,.015,(f-.5)*.54],[l*(2.4+f*.65),.02,(f-.5)*.25]],.009,n,d)}}for(let u=0;u<3;u++)s.tube([[l*.23,.45,.3-u*.4],[l*.55,-.05,.6-u*.45],[l*.8,-.25,.9-u*.5]],.025,n,t)}}else if(e.kind==="golem"){for(let[o,c,l,h,u,d]of[[0,.6,0,1,1.25,.55],[0,2,0,.7,.6,.7],[-1.1,.7,0,.65,.8,.6],[1.1,.7,0,.65,.8,.6],[-.5,-.9,0,.45,.7,.5],[.5,-.9,0,.45,.7,.5]])a(new Vt(1,1),s.materials.darkStone,o,c,l,h,u,d);for(let o of[-1,1])a(new Mn(.24,.08,.1),r,o*.25,2.12,.6);a(new Hn(.35),r,0,.8,.58,1,1.4,1)}else if(e.kind==="phoenix"){let o=new nt({color:7286052,metalness:.5,roughness:.44,emissive:6826766,emissiveIntensity:.5});a(new Nt(1,20,12),o,0,.7,0,.5,.7,.9),a(new os(.2,.65,6),n,0,1.4,.9).rotation.x=Math.PI/2;for(let c of[-1,1])for(let l=0;l<7;l++){let h=a(new os(.18,2.2-l*.1,6),l%2?o:n,c*(.9+l*.23),.6-l*.11,0,.9,1,.4);h.rotation.z=-c*(.55+l*.08)}for(let c=0;c<4;c++)s.tube([[0,.1,-.5],[(c-1.5)*.35,-.7,-1.3],[(c-1.5)*.7,-1.5,-2.4]],.065,c%2?r:n,t)}else if(e.kind==="thunderlord"){a(new os(1.35,3.5,8),n,0,.3,0),a(new Vt(.6,1),n,0,2.5,.1);for(let o=0;o<5;o++){let c=o*Math.PI*2/5,l=a(new os(.13,1.2,5),r,Math.cos(c)*.65,3+Math.sin(c)*.5,-.2);l.rotation.z=-c}for(let o of[-1,1])s.tube([[o*.7,1.4,0],[o*1.6,1.1,0],[o*2.2,1.7,.4]],.14,n,t),a(new Hn(.45),new Ye({color:11903743}),o*2.2,1.7,.4);a(new si(2.3,.06,8,80),r,0,1,-.8)}else return null;return t.userData.special=!0,t}function $p(s){let e=s.materials;s.realmGroups=[];let t=new Ke;t.position.set(yt.x,yt.y,yt.z),t.visible=!1,s.scene.add(t),s.realmGroups[2]=t;let n=new Ee(new Rt(110,70),new It({color:2778733,roughness:.06,metalness:.65,clearcoat:1,transparent:!0,opacity:.94}));n.rotation.x=-Math.PI/2,n.position.set(0,-.35,-122),t.add(n),s.lakeWater=n,s.waterRipples=[],s.box(e.stone,0,-.45,-118,9,.8,37,t);let i=new nt({color:10272425,map:e.stone.map,normalMap:e.stone.normalMap,roughness:.58});s.box(i,0,.005,-118,9,.06,37,t);for(let c of[-9,9])for(let l=-105;l>=-136;l-=9){s.cylinder(i,.38,.52,7,c,3.1,l,t,20),s.cylinder(e.metal,.65,.65,.14,c,6.7,l,t,20);let h=new Ee(new si(1.5,.08,8,48),e.metal);h.position.set(c,4.8,l),h.rotation.y=c<0?.6:-.6,t.add(h)}for(let c=0;c<7;c++){let l=new Ee(new ki(2.5+c*1.1,2.52+c*1.1,64),new Ye({color:9491135,transparent:!0,opacity:.11,side:st}));l.rotation.x=-Math.PI/2,l.position.set((c%2?1:-1)*12,-.31,-113-c*3),t.add(l),s.waterRipples.push(l)}let r=new Ke;r.visible=!1,s.scene.add(r),s.realmGroups[3]=r,s.cylinder(e.darkStone,15,17,3,0,-1.6,-170,r,32),s.box(e.darkStone,0,-.15,-157,9,.5,22,r);let a=new Ye({color:16414782,toneMapped:!1});for(let c=0;c<14;c++){let l=c*Math.PI*2/14,h=Math.cos(l)*18,u=-170+Math.sin(l)*18,d=s.mesh(new Vt(1,1),e.darkStone,h,3,u,1.2,4+c%4,1.2,r);d.rotation.z=(c%3-1)*.12,s.box(e.metal,h,7+c%3,u,.12,3,.12,r)}for(let c=0;c<6;c++){let l=c*Math.PI/3;s.tube([[Math.cos(l)*2,.02,-170+Math.sin(l)*2],[Math.cos(l)*7,.02,-170+Math.sin(l)*7],[Math.cos(l+.1)*13,.02,-170+Math.sin(l+.1)*13]],.045,a,r)}let o=new Ee(new Rt(25,25),new Ye({map:s.runes,color:11238622,transparent:!0,opacity:.3,blending:dt,depthWrite:!1}));o.rotation.x=-Math.PI/2,o.position.set(0,.03,-170),r.add(o),s.realmRune=o}var $t=[{name:"\u5931\u5E8F\u5C71\u95E8",subtitle:"\u7834\u5F00\u5C71\u95E8\uFF0C\u627E\u56DE\u638C\u7EB9\u4E2D\u7684\u8DEF",camera:{x:0,z:13},enemies:[{id:"gate-wisp",kind:"wisp",name:"\u6E38\u9B47",hp:88,x:-5,z:-3,delay:1.8},{id:"gate-shade",kind:"shade",name:"\u63A0\u5F71",hp:104,x:5,z:-8,delay:3.6},{id:"gate-keeper",kind:"keeper",name:"\u5B88\u5C71\u591C\u9B47",hp:240,x:0,z:-15,delay:6}]},{name:"\u60AC\u5929\u7D22\u6865",subtitle:"\u4E00\u7EBF\u60AC\u6865\uFF0C\u4E91\u4E0B\u6709\u9B47 \xB7 \u8FDE\u5251\u622A\u65AD\u873B\u8713\u5996\u6251\u51FB",camera:{x:0,z:-43},enemies:[{id:"bridge-shade",kind:"manta",name:"\u5DE1\u4E91\u9CD0",hp:112,x:-4,z:-58,delay:.9},{id:"bridge-wisp",kind:"manta",name:"\u88C2\u98CE\u4E91\u9CD0",hp:96,x:4,z:-53,delay:2.6},{id:"bridge-keeper",kind:"dragonfly",name:"\u7409\u7483\u873B\u8713\u5996",hp:360,x:0,z:-69,delay:5.5}]},{name:"\u955C\u6E56\u56DE\u5ECA",subtitle:"\u5148\u7ED3\u7834\u90AA\u5370\u7834\u955C\u969C\uFF0C\u518D\u8FDB\u653B",camera:{...Sc},enemies:[{id:"lake-reflection-a",kind:"reflection",name:"\u6D41\u5149\u955C\u5F71",hp:112,x:yt.x+-4,z:yt.z+-116,delay:1},{id:"lake-reflection-b",kind:"reflection",name:"\u5BD2\u7389\u955C\u5F71",hp:112,x:yt.x+4,z:yt.z+-120,delay:2.3},{id:"lake-mirror",kind:"mirror",name:"\u955C\u6E56\u7075\u9B44",hp:288,x:yt.x+0,z:yt.z+-128,delay:4.5}]},{name:"\u96F7\u72F1\u5929\u53F0",subtitle:"\u907F\u5F00\u5730\u9762\u96F7\u5708\uFF0C\u4EE5\u4E94\u96F7\u8BC0\u7834\u7532",camera:{x:0,z:-155},enemies:[{id:"storm-phoenix",kind:"phoenix",name:"\u711A\u7FBD\u5996\u51F0",hp:156,x:-5,z:-168,delay:1},{id:"storm-golem",kind:"golem",name:"\u96F7\u94F8\u77F3\u5080",hp:220,x:5,z:-172,delay:2.8},{id:"storm-lord",kind:"thunderlord",name:"\u6267\u96F7\u5929\u50CF",hp:420,x:0,z:-181,delay:5.5}]}];var jp=$t.reduce((s,e)=>s+e.enemies.length,0);var Qp=(s=0,e=0,t=0)=>new R(s,e,t),Tc=class{constructor(e){this.world=e,this.map=new Map,e.enemy.visible=!1;for(let t of $t.flatMap(n=>n.enemies)){let n=Jp(e,t)||e.enemy.clone(!0);n.visible=!1,n.traverse(o=>{(o.isMesh||o.isSprite)&&(o.material=o.material.clone(),o.isMesh&&(o.castShadow=!0,o.receiveShadow=!0))});let i={keeper:1,shade:.8,wisp:.62,manta:.95,dragonfly:1.15,reflection:.9,mirror:1.15,golem:1.2,phoenix:1.05,thunderlord:1.15}[t.kind]||1;n.scale.setScalar(i);let r=[];if(["shade","wisp"].includes(t.kind)){let o=new It({color:t.kind==="shade"?1193021:2898742,emissive:t.kind==="shade"?1389892:2308137,emissiveIntensity:.6,roughness:.52,metalness:.35,side:st,transparent:!0,opacity:.87});for(let c of[-1,1]){let l=new Ke;n.add(l),l.position.set(c*.45,.7,-.1);for(let h=0;h<4;h++){let u=new Vn;u.moveTo(0,0),u.quadraticCurveTo(c*(2.1+h*.25),1.1-h*.13,c*(3.1-h*.4),.7-h*.55),u.quadraticCurveTo(c*1.7,-.9-h*.28,0,-.3);let d=new Ee(new ls(u,14),o);d.position.z=-h*.11,l.add(d)}r.push({wing:l,sign:c})}}let a=new Cn(new vn({map:e.glow,color:t.kind==="wisp"?8443837:t.kind==="shade"?8627694:14984559,transparent:!0,opacity:.13,blending:dt,depthWrite:!1}));a.scale.set(7,7,1),a.position.y=.7,n.add(a),e.scene.add(n),this.map.set(t.id,{root:n,wings:r,scale:i,glow:a,kind:t.kind,born:-1,dead:-1,hit:0})}}position(e){return this.map.get(e)?.root.position.clone().add(Qp(0,.65,.3))}hit(e){let t=this.map.get(e);t&&(t.hit=1)}reset(){for(let e of this.map.values())e.root.visible=!1,e.born=-1,e.dead=-1,e.hit=0}update(e,t,n){let i=new Map((t.enemies||[]).map(r=>[r.id,r]));for(let[r,a]of this.map){let o=i.get(r);if(!o||!o.visible){a.root.visible=!1;continue}if(a.born<0&&(a.born=n),!o.alive){a.dead<0&&(a.dead=n);let l=(n-a.dead)/.85;a.root.visible=l<1,a.root.scale.setScalar(a.scale*(1-.14*l)*Math.max(.01,1-Math.max(0,l-.65)/.35)),a.root.position.y=o.y-Math.min(l,.65)*1.8,a.root.rotation.x=-l*.9,a.root.rotation.z=l*.55;continue}a.root.visible=!0;let c=Math.min(1,(n-a.born)/.5);a.root.scale.setScalar(a.scale*(.15+.85*c)),a.root.position.set(o.x,o.y,o.z),a.root.rotation.set(Math.sin(n*2)*.03,Math.atan2(this.world.camera.position.x-o.x,this.world.camera.position.z-o.z),Math.sin(n*1.3)*.025),o.dodging&&(a.root.rotation.z+=Math.sin(n*18)*.3),o.kind==="dragonfly"&&(a.root.rotation.x=.3+Math.sin(n*3)*.08+(o.incoming?-.45:0),a.root.rotation.y+=.35+Math.sin(n*1.8)*.18,a.root.traverse(l=>{if(l.userData.dragonWing){let{side:h,pair:u}=l.userData.dragonWing;l.rotation.z=h*(.28+Math.sin(n*(o.incoming?72:43)+u*.6)*.4)}l.userData.demonEye&&(l.material.emissive.set(o.incoming?16717883:5487768),l.material.emissiveIntensity=o.incoming?3.5:.6)}));for(let l of a.root.children)l.userData.flap&&(l.rotation.z=l.userData.flap*Math.sin(n*4)*.3),l.userData.segment!==void 0&&(l.position.x+=Math.sin(n*3+l.userData.segment*.5)*e*.45);a.hit=Math.max(0,a.hit-e*5),a.glow.material.opacity=.1+a.hit*.35+(o.incoming?.12:0)+(o.shielded?.12:0),a.glow.material.color.set(o.shielded?8557823:o.incoming?16741972:r===t.targetId?11397328:7905212);for(let{wing:l,sign:h}of a.wings)l.rotation.y=h*(.3+Math.sin(n*(o.kind==="shade"?8:4))*.45),l.rotation.z=h*Math.sin(n*3)*.15}}project(e,t,n){let i=[];for(let[r,a]of this.map){if(!a.root.visible||a.dead>=0)continue;let o=a.root.position.clone().add(Qp(0,a.scale*3.4,0)).project(e);o.z<1&&o.z>0&&Math.abs(o.x)<1.15&&Math.abs(o.y)<1.15&&i.push({id:r,x:(o.x*.5+.5)*t,y:(-.5*o.y+.5)*n})}return i}};function em(s){let e=s.materials,t=new Ke;t.name="cliff-suspension-bridge",s.bridgeGroup=t,s.scene.add(t),s.box(e.stone,0,.85,-33,5.8,1.4,5.4,t);for(let[f,m,_,b]of[[0,-23,18,10],[-19,-45,7,5],[20,-66,8,6]]){let x=s.mesh(new Vt(1,2),e.stone,f,-29,m,_,31,b,t);x.rotation.y=.12,s.mesh(new Vt(1,1),e.darkStone,f,-51,m,_*.7,20,b*.7,t)}let n=fn;s.mesh(new Vt(1,2),e.stone,n.x,n.y-4,n.z+1,3.5,4,4,t);let i=document.createElement("canvas");i.width=512,i.height=128;let r=i.getContext("2d");r.fillStyle="#78634b",r.fillRect(0,0,512,128);for(let f=0;f<180;f++){r.strokeStyle=f%3?"#322b2530":"#c0a17b38",r.lineWidth=f%4===0?2:.7,r.beginPath();for(let m=0;m<=512;m+=16){let _=f*.73%128+Math.sin(m*.023+f)*1.4;m?r.lineTo(m,_):r.moveTo(m,_)}r.stroke()}let a=new Mi(i);a.colorSpace=Ct;let o=new nt({map:a,color:11117202,roughness:.95}),c=new nt({color:10587237,roughness:1}),l=Math.ceil((xt.start-xt.end)/.46)+1,h=new un(new Mn(1,.14,.43),o,l),u=new ft;for(let f=0;f<l;f++){let m=xt.start+(xt.end-xt.start)*f/(l-1),_=eo(m,Math.sin(f*7.1)*.025,-.07);u.position.set(_.x,_.y,_.z),u.rotation.set(Math.atan((Ki(m-.05)-Ki(m+.05))/.1),wu(m)+Math.sin(f*9)*.013,Math.sin(f*5)*.012),u.scale.set(xt.width+Math.sin(f*17)*.09,1,1),u.updateMatrix(),h.setMatrixAt(f,u.matrix),h.setColorAt(f,new Me().setScalar(.76+(Math.sin(f*19)+1)*.12))}h.castShadow=!0,h.receiveShadow=!0,t.add(h);for(let f of[-.79,.79]){for(let b of[-.19,.52,1.22])s.tube(Array.from({length:49},(x,T)=>{let S=xt.start+(xt.end-xt.start)*T/48,A=eo(S,f,b);return[A.x,A.y,A.z]}),b===1.22?.055:.035,c,t);let m=Math.ceil((xt.start-xt.end)/1.4)+1,_=new un(new _n(.025,.025,1.45,6),c,m);for(let b=0;b<m;b++){let x=xt.start+(xt.end-xt.start)*b/(m-1),T=eo(x,f,.5);u.position.set(T.x,T.y,T.z),u.rotation.set(0,0,Math.sin(b*7)*.025),u.scale.set(1,1,1),u.updateMatrix(),_.setMatrixAt(b,u.matrix)}t.add(_);for(let b of[xt.start+.3,xt.end-.3]){let x=eo(b,f);s.cylinder(e.woodLight,.13,.17,3,x.x,x.y+1,x.z,t);for(let T of[x.y+.35,x.y+1.2])s.cylinder(c,.18,.18,.15,x.x,T,x.z,t);s.mesh(new Nt(.18,8,8),e.metal,x.x,x.y+2.5,x.z,1,1,1,t)}}for(let f of[-2.4,2.4])s.lantern(f,-32.5);for(let f=0;f<12;f++){let _=(f%2?1:-1)*(15+f%4*7),b=-42-f*4;s.mesh(new Vt(1,1),f%2?e.stone:e.darkStone,_,-20-f%3*8,b,3+f%3,21+f%4*5,4,t)}let d=document.createElement("canvas");d.width=d.height=256;let p=d.getContext("2d"),g=p.createRadialGradient(128,128,0,128,128,128);g.addColorStop(0,"#c6dfdf50"),g.addColorStop(1,"#c6dfdf00"),p.fillStyle=g,p.fillRect(0,0,256,256);let v=new Mi(d);s.clouds=[];for(let f=0;f<24;f++){let m=new Cn(new vn({map:v,color:11981013,transparent:!0,opacity:.58,depthWrite:!1}));m.position.set((f%2?1:-1)*(4+f%5*5),-9-f%4*5,-35-f*2.5),m.scale.set(29,8,1),t.add(m),s.clouds.push(m)}}function tm(){let s=new It({color:13145977,roughness:.65,metalness:0,clearcoat:.04,sheen:.24,sheenColor:15252650,sheenRoughness:.8});s.onBeforeCompile=t=>{t.vertexShader=t.vertexShader.replace("#include <common>",`#include <common>
varying vec3 vSkinP;
varying vec3 vSkinN;`).replace("#include <begin_vertex>",`#include <begin_vertex>
vSkinP=position;vSkinN=normal;`),t.fragmentShader=t.fragmentShader.replace("#include <common>",`#include <common>
   varying vec3 vSkinP;varying vec3 vSkinN;
   float skinNoise(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
   float nail(vec2 p,vec2 c,vec2 size){vec2 q=abs((p-c)/size);return 1.0-smoothstep(.8,1.0,pow(pow(q.x,4.0)+pow(q.y,4.0),.25));}
  `).replace("#include <color_fragment>",`#include <color_fragment>
   vec3 p=vSkinP;float pore=skinNoise(floor(p*7200.0)),mottling=skinNoise(floor(p*420.0));
   diffuseColor.rgb*=1.0+(pore-.5)*.035+(mottling-.5)*.025;
   float vein=exp(-pow(sin(p.z*150.0+p.y*45.0)*7.0,2.0))*(1.0-smoothstep(.0,.03,abs(p.y+.008)));
   diffuseColor.rgb=mix(diffuseColor.rgb,diffuseColor.rgb*vec3(.9,.96,.96),vein*.16);
   float nMask=nail(p.zy,vec2(-.011,-.108),vec2(.0046,.0055))+nail(p.zy,vec2(.015,-.116),vec2(.0048,.0055))+nail(p.zy,vec2(.043,-.102),vec2(.0045,.005))+nail(p.zy,vec2(.060,-.077),vec2(.0036,.0045));
   nMask=clamp(nMask,0.0,1.0)*smoothstep(.3,.75,vSkinN.x);
   // A thin pink nail bed follows the same skin weights as its fingertip.
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.60,.35,.27),nMask*.32);
   float warmth=exp(-pow((p.y+.075)*28.0,2.0));diffuseColor.rgb*=mix(vec3(1.0),vec3(1.045,.965,.94),warmth*.55);
   float knuckle=exp(-pow((p.y+.078)*1050.0,2.0))*exp(-pow((p.z+.013)*90.0,2.0))+exp(-pow((p.y+.083)*1050.0,2.0))*exp(-pow((p.z-.012)*100.0,2.0))+exp(-pow((p.y+.071)*1050.0,2.0))*exp(-pow((p.z-.036)*100.0,2.0))+exp(-pow((p.y+.052)*1050.0,2.0))*exp(-pow((p.z-.053)*100.0,2.0));
   diffuseColor.rgb*=1.0-knuckle*.10*smoothstep(.35,.8,vSkinN.x);

  `).replace("#include <roughnessmap_fragment>",`#include <roughnessmap_fragment>
roughnessFactor=clamp(roughnessFactor+(skinNoise(floor(vSkinP*6200.0))-.5)*.065,.5,.8);roughnessFactor=mix(roughnessFactor,.38,nMask);`)};let e=s.onBeforeCompile;return s.onBeforeCompile=t=>{e(t),t.fragmentShader=t.fragmentShader.replace("#include <normal_fragment_maps>",`#include <normal_fragment_maps>
 vec3 grain=vec3(sin(vSkinP.y*5200.0)*sin(vSkinP.z*4500.0),sin(vSkinP.x*4700.0)*sin(vSkinP.y*5800.0),sin(vSkinP.z*6100.0)*sin(vSkinP.x*4900.0));normal=normalize(normal+grain*.026*(1.0-nMask));`)},s.customProgramCacheKey=()=>"yuanli-skin-moonlight-v4",s}function nm(s){let e=s.attributes.position,t=s.attributes.skinIndex,n=s.attributes.skinWeight;if(!t||!n)return s;let i=[],r=[],a=new Map,o=[];for(let m=0;m<e.count;m++){let _=[0,1,2,3].map(T=>t.array[m*4+T]),b=[0,1,2,3].map(T=>n.array[m*4+T]),x=[e.getX(m),e.getY(m),e.getZ(m)].map(T=>Math.round(T*1e6)).join(",")+"|"+_.map((T,S)=>`${T}:${Math.round(b[S]*1e4)}`).join(",");a.has(x)||(a.set(x,i.length),i.push(new R(e.getX(m),e.getY(m),e.getZ(m))),r.push(_.map((T,S)=>[T,b[S]]))),o.push(a.get(x))}let c=s.index?Array.from(s.index.array):Array.from({length:e.count},(m,_)=>_),l=[];for(let m=0;m<c.length;m+=3)l.push(c.slice(m,m+3).map(_=>o[_]));let h=i.map(()=>new Set),u=new Map,d=(m,_)=>m<_?`${m},${_}`:`${_},${m}`;for(let[m,_,b]of l)for(let[x,T,S]of[[m,_,b],[_,b,m],[b,m,_]]){h[x].add(T),h[T].add(x);let A=d(x,T);u.has(A)||u.set(A,{a:x,b:T,opposite:[]}),u.get(A).opposite.push(S)}let p=m=>{let _=new R,b=new Map;for(let[S,A]of m){_.addScaledVector(i[S],A);for(let[y,E]of r[S])b.set(y,(b.get(y)||0)+E*A)}let x=[...b].sort((S,A)=>A[1]-S[1]).slice(0,4),T=x.reduce((S,A)=>S+A[1],0)||1;for(;x.length<4;)x.push([0,0]);return{pos:_,skin:x.map(([S,A])=>[S,A/T])}},g=[];for(let m=0;m<i.length;m++){let _=[...h[m]].filter(b=>u.get(d(m,b)).opposite.length===1);if(_.length===2)g.push(p([[m,.75],[_[0],.125],[_[1],.125]]));else{let b=h[m].size,x=b===3?3/16:3/(8*Math.max(1,b));g.push(p([[m,1-b*x],...[...h[m]].map(T=>[T,x])]))}}for(let m of u.values())m.mid=g.length,g.push(p(m.opposite.length===2?[[m.a,.375],[m.b,.375],...[...m.opposite].map(_=>[_,.125])]:[[m.a,.5],[m.b,.5]]));let v=[];for(let[m,_,b]of l){let x=u.get(d(m,_)).mid,T=u.get(d(_,b)).mid,S=u.get(d(b,m)).mid;v.push(m,x,S,_,T,x,b,S,T,x,T,S)}let f=new tt;return f.setAttribute("position",new Oe(g.flatMap(m=>m.pos.toArray()),3)),f.setAttribute("skinIndex",new Es(g.flatMap(m=>m.skin.map(_=>_[0])),4)),f.setAttribute("skinWeight",new Oe(g.flatMap(m=>m.skin.map(_=>_[1])),4)),f.setIndex(v),f.computeVertexNormals(),f.computeBoundingSphere(),f}function im(s){s.nails=[]}var zr={name:"CopyShader",uniforms:{tDiffuse:{value:null},opacity:{value:1}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform float opacity;

		uniform sampler2D tDiffuse;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );
			gl_FragColor = opacity * texel;


		}`};var Fn=class{constructor(){this.isPass=!0,this.enabled=!0,this.needsSwap=!0,this.clear=!1,this.renderToScreen=!1}setSize(){}render(){console.error("THREE.Pass: .render() must be implemented in derived pass.")}dispose(){}},sM=new Ti(-1,1,1,-1,0,1),Eu=class extends tt{constructor(){super(),this.setAttribute("position",new Oe([-1,3,0,-1,-1,0,3,-1,0],3)),this.setAttribute("uv",new Oe([0,2,0,0,2,0],2))}},rM=new Eu,ms=class{constructor(e){this._mesh=new Ee(rM,e)}dispose(){this._mesh.geometry.dispose()}render(e){e.render(this._mesh,sM)}get material(){return this._mesh.material}set material(e){this._mesh.material=e}};var wc=class extends Fn{constructor(e,t="tDiffuse"){super(),this.textureID=t,this.uniforms=null,this.material=null,e instanceof Bt?(this.uniforms=e.uniforms,this.material=e):e&&(this.uniforms=qi.clone(e.uniforms),this.material=new Bt({name:e.name!==void 0?e.name:"unspecified",defines:Object.assign({},e.defines),uniforms:this.uniforms,vertexShader:e.vertexShader,fragmentShader:e.fragmentShader})),this._fsQuad=new ms(this.material)}render(e,t,n){this.uniforms[this.textureID]&&(this.uniforms[this.textureID].value=n.texture),this._fsQuad.material=this.material,this.renderToScreen?(e.setRenderTarget(null),this._fsQuad.render(e)):(e.setRenderTarget(t),this.clear&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),this._fsQuad.render(e))}dispose(){this.material.dispose(),this._fsQuad.dispose()}};var to=class extends Fn{constructor(e,t){super(),this.scene=e,this.camera=t,this.clear=!0,this.needsSwap=!1,this.inverse=!1}render(e,t,n){let i=e.getContext(),r=e.state;r.buffers.color.setMask(!1),r.buffers.depth.setMask(!1),r.buffers.color.setLocked(!0),r.buffers.depth.setLocked(!0);let a,o;this.inverse?(a=0,o=1):(a=1,o=0),r.buffers.stencil.setTest(!0),r.buffers.stencil.setOp(i.REPLACE,i.REPLACE,i.REPLACE),r.buffers.stencil.setFunc(i.ALWAYS,a,4294967295),r.buffers.stencil.setClear(o),r.buffers.stencil.setLocked(!0),e.setRenderTarget(n),this.clear&&e.clear(),e.render(this.scene,this.camera),e.setRenderTarget(t),this.clear&&e.clear(),e.render(this.scene,this.camera),r.buffers.color.setLocked(!1),r.buffers.depth.setLocked(!1),r.buffers.color.setMask(!0),r.buffers.depth.setMask(!0),r.buffers.stencil.setLocked(!1),r.buffers.stencil.setFunc(i.EQUAL,1,4294967295),r.buffers.stencil.setOp(i.KEEP,i.KEEP,i.KEEP),r.buffers.stencil.setLocked(!0)}},Ac=class extends Fn{constructor(){super(),this.needsSwap=!1}render(e){e.state.buffers.stencil.setLocked(!1),e.state.buffers.stencil.setTest(!1)}};var Ec=class{constructor(e,t){if(this.renderer=e,this._pixelRatio=e.getPixelRatio(),t===void 0){let n=e.getSize(new ne);this._width=n.width,this._height=n.height,t=new Jt(this._width*this._pixelRatio,this._height*this._pixelRatio,{type:an}),t.texture.name="EffectComposer.rt1"}else this._width=t.width,this._height=t.height;this.renderTarget1=t,this.renderTarget2=t.clone(),this.renderTarget2.texture.name="EffectComposer.rt2",this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2,this.renderToScreen=!0,this.passes=[],this.copyPass=new wc(zr),this.copyPass.material.blending=Xn,this.timer=new Fa}swapBuffers(){let e=this.readBuffer;this.readBuffer=this.writeBuffer,this.writeBuffer=e}addPass(e){this.passes.push(e),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}insertPass(e,t){this.passes.splice(t,0,e),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}removePass(e){let t=this.passes.indexOf(e);t!==-1&&this.passes.splice(t,1)}isLastEnabledPass(e){for(let t=e+1;t<this.passes.length;t++)if(this.passes[t].enabled)return!1;return!0}render(e){this.timer.update(),e===void 0&&(e=this.timer.getDelta());let t=this.renderer.getRenderTarget(),n=!1;for(let i=0,r=this.passes.length;i<r;i++){let a=this.passes[i];if(a.enabled!==!1){if(a.renderToScreen=this.renderToScreen&&this.isLastEnabledPass(i),a.render(this.renderer,this.writeBuffer,this.readBuffer,e,n),a.needsSwap){if(n){let o=this.renderer.getContext(),c=this.renderer.state.buffers.stencil;c.setFunc(o.NOTEQUAL,1,4294967295),this.copyPass.render(this.renderer,this.writeBuffer,this.readBuffer,e),c.setFunc(o.EQUAL,1,4294967295)}this.swapBuffers()}to!==void 0&&(a instanceof to?n=!0:a instanceof Ac&&(n=!1))}}this.renderer.setRenderTarget(t)}reset(e){if(e===void 0){let t=this.renderer.getSize(new ne);this._pixelRatio=this.renderer.getPixelRatio(),this._width=t.width,this._height=t.height,e=this.renderTarget1.clone(),e.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.renderTarget1=e,this.renderTarget2=e.clone(),this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2}setSize(e,t){this._width=e,this._height=t;let n=this._width*this._pixelRatio,i=this._height*this._pixelRatio;this.renderTarget1.setSize(n,i),this.renderTarget2.setSize(n,i);for(let r=0;r<this.passes.length;r++)this.passes[r].setSize(n,i)}setPixelRatio(e){this._pixelRatio=e,this.setSize(this._width,this._height)}dispose(){this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.copyPass.dispose()}};var Cc=class extends Fn{constructor(e,t,n=null,i=null,r=null){super(),this.scene=e,this.camera=t,this.overrideMaterial=n,this.clearColor=i,this.clearAlpha=r,this.clear=!0,this.clearDepth=!1,this.needsSwap=!1,this.isRenderPass=!0,this._oldClearColor=new Me}render(e,t,n){let i=e.autoClear;e.autoClear=!1;let r,a;this.overrideMaterial!==null&&(a=this.scene.overrideMaterial,this.scene.overrideMaterial=this.overrideMaterial),this.clearColor!==null&&(e.getClearColor(this._oldClearColor),e.setClearColor(this.clearColor,e.getClearAlpha())),this.clearAlpha!==null&&(r=e.getClearAlpha(),e.setClearAlpha(this.clearAlpha)),this.clearDepth==!0&&e.clearDepth(),e.setRenderTarget(this.renderToScreen?null:n),this.clear===!0&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),e.render(this.scene,this.camera),this.clearColor!==null&&e.setClearColor(this._oldClearColor),this.clearAlpha!==null&&e.setClearAlpha(r),this.overrideMaterial!==null&&(this.scene.overrideMaterial=a),e.autoClear=i}};var sm={name:"LuminosityHighPassShader",uniforms:{tDiffuse:{value:null},luminosityThreshold:{value:1},smoothWidth:{value:1},defaultColor:{value:new Me(0)},defaultOpacity:{value:0}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;

			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform sampler2D tDiffuse;
		uniform vec3 defaultColor;
		uniform float defaultOpacity;
		uniform float luminosityThreshold;
		uniform float smoothWidth;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );

			float v = luminance( texel.xyz );

			vec4 outputColor = vec4( defaultColor.rgb, defaultOpacity );

			float alpha = smoothstep( luminosityThreshold, luminosityThreshold + smoothWidth, v );

			gl_FragColor = mix( outputColor, texel, alpha );

		}`};var Gr=class s extends Fn{constructor(e,t=1,n,i){super(),this.strength=t,this.radius=n,this.threshold=i,this.resolution=e!==void 0?new ne(e.x,e.y):new ne(256,256),this.clearColor=new Me(0,0,0),this.needsSwap=!1,this.renderTargetsHorizontal=[],this.renderTargetsVertical=[],this.nMips=5;let r=Math.round(this.resolution.x/2),a=Math.round(this.resolution.y/2);this.renderTargetBright=new Jt(r,a,{type:an,depthBuffer:!1}),this.renderTargetBright.texture.name="UnrealBloomPass.bright",this.renderTargetBright.texture.generateMipmaps=!1;for(let h=0;h<this.nMips;h++){let u=new Jt(r,a,{type:an,depthBuffer:!1});u.texture.name="UnrealBloomPass.h"+h,u.texture.generateMipmaps=!1,this.renderTargetsHorizontal.push(u);let d=new Jt(r,a,{type:an,depthBuffer:!1});d.texture.name="UnrealBloomPass.v"+h,d.texture.generateMipmaps=!1,this.renderTargetsVertical.push(d),r=Math.round(r/2),a=Math.round(a/2)}let o=sm;this.highPassUniforms=qi.clone(o.uniforms),this.highPassUniforms.luminosityThreshold.value=i,this.highPassUniforms.smoothWidth.value=.01,this.materialHighPassFilter=new Bt({uniforms:this.highPassUniforms,vertexShader:o.vertexShader,fragmentShader:o.fragmentShader}),this.separableBlurMaterials=[];let c=[6,10,14,18,22];r=Math.round(this.resolution.x/2),a=Math.round(this.resolution.y/2);for(let h=0;h<this.nMips;h++)this.separableBlurMaterials.push(this._getSeparableBlurMaterial(c[h])),this.separableBlurMaterials[h].uniforms.invSize.value=new ne(1/r,1/a),r=Math.round(r/2),a=Math.round(a/2);this.compositeMaterial=this._getCompositeMaterial(this.nMips),this.compositeMaterial.uniforms.blurTexture1.value=this.renderTargetsVertical[0].texture,this.compositeMaterial.uniforms.blurTexture2.value=this.renderTargetsVertical[1].texture,this.compositeMaterial.uniforms.blurTexture3.value=this.renderTargetsVertical[2].texture,this.compositeMaterial.uniforms.blurTexture4.value=this.renderTargetsVertical[3].texture,this.compositeMaterial.uniforms.blurTexture5.value=this.renderTargetsVertical[4].texture,this.compositeMaterial.uniforms.bloomStrength.value=t,this.compositeMaterial.uniforms.bloomRadius.value=.1;let l=[1,.8,.6,.4,.2];this.compositeMaterial.uniforms.bloomFactors.value=l,this.bloomTintColors=[new R(1,1,1),new R(1,1,1),new R(1,1,1),new R(1,1,1),new R(1,1,1)],this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors,this.copyUniforms=qi.clone(zr.uniforms),this.blendMaterial=new Bt({uniforms:this.copyUniforms,vertexShader:zr.vertexShader,fragmentShader:zr.fragmentShader,premultipliedAlpha:!0,blending:dt,depthTest:!1,depthWrite:!1,transparent:!0}),this._oldClearColor=new Me,this._oldClearAlpha=1,this._basic=new Ye,this._fsQuad=new ms(null)}dispose(){for(let e=0;e<this.renderTargetsHorizontal.length;e++)this.renderTargetsHorizontal[e].dispose();for(let e=0;e<this.renderTargetsVertical.length;e++)this.renderTargetsVertical[e].dispose();this.renderTargetBright.dispose();for(let e=0;e<this.separableBlurMaterials.length;e++)this.separableBlurMaterials[e].dispose();this.compositeMaterial.dispose(),this.blendMaterial.dispose(),this._basic.dispose(),this._fsQuad.dispose()}setSize(e,t){let n=Math.round(e/2),i=Math.round(t/2);this.renderTargetBright.setSize(n,i);for(let r=0;r<this.nMips;r++)this.renderTargetsHorizontal[r].setSize(n,i),this.renderTargetsVertical[r].setSize(n,i),this.separableBlurMaterials[r].uniforms.invSize.value=new ne(1/n,1/i),n=Math.round(n/2),i=Math.round(i/2)}render(e,t,n,i,r){e.getClearColor(this._oldClearColor),this._oldClearAlpha=e.getClearAlpha();let a=e.autoClear;e.autoClear=!1,e.setClearColor(this.clearColor,0),r&&e.state.buffers.stencil.setTest(!1),this.renderToScreen&&(this._fsQuad.material=this._basic,this._basic.map=n.texture,e.setRenderTarget(null),e.clear(),this._fsQuad.render(e)),this.highPassUniforms.tDiffuse.value=n.texture,this.highPassUniforms.luminosityThreshold.value=this.threshold,this._fsQuad.material=this.materialHighPassFilter,e.setRenderTarget(this.renderTargetBright),e.clear(),this._fsQuad.render(e);let o=this.renderTargetBright;for(let c=0;c<this.nMips;c++)this._fsQuad.material=this.separableBlurMaterials[c],this.separableBlurMaterials[c].uniforms.colorTexture.value=o.texture,this.separableBlurMaterials[c].uniforms.direction.value=s.BlurDirectionX,e.setRenderTarget(this.renderTargetsHorizontal[c]),e.clear(),this._fsQuad.render(e),this.separableBlurMaterials[c].uniforms.colorTexture.value=this.renderTargetsHorizontal[c].texture,this.separableBlurMaterials[c].uniforms.direction.value=s.BlurDirectionY,e.setRenderTarget(this.renderTargetsVertical[c]),e.clear(),this._fsQuad.render(e),o=this.renderTargetsVertical[c];this._fsQuad.material=this.compositeMaterial,this.compositeMaterial.uniforms.bloomStrength.value=this.strength,this.compositeMaterial.uniforms.bloomRadius.value=this.radius,this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors,e.setRenderTarget(this.renderTargetsHorizontal[0]),e.clear(),this._fsQuad.render(e),this._fsQuad.material=this.blendMaterial,this.copyUniforms.tDiffuse.value=this.renderTargetsHorizontal[0].texture,r&&e.state.buffers.stencil.setTest(!0),this.renderToScreen?(e.setRenderTarget(null),this._fsQuad.render(e)):(e.setRenderTarget(n),this._fsQuad.render(e)),e.setClearColor(this._oldClearColor,this._oldClearAlpha),e.autoClear=a}_getSeparableBlurMaterial(e){let t=[],n=e/3;for(let a=0;a<e;a++)t.push(.39894*Math.exp(-.5*a*a/(n*n))/n);let i=[],r=[];for(let a=1;a<e;a+=2){let o=t[a],c=a+1<e?t[a+1]:0,l=o+c;i.push((a*o+(a+1)*c)/l),r.push(l)}return new Bt({defines:{KERNEL_PAIRS:i.length},uniforms:{colorTexture:{value:null},invSize:{value:new ne(.5,.5)},direction:{value:new ne(.5,.5)},centerWeight:{value:t[0]},gaussianOffsets:{value:i},gaussianWeights:{value:r}},vertexShader:`

				varying vec2 vUv;

				void main() {

					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

				}`,fragmentShader:`

				#include <common>

				varying vec2 vUv;

				uniform sampler2D colorTexture;
				uniform vec2 invSize;
				uniform vec2 direction;
				uniform float centerWeight;
				uniform float gaussianOffsets[KERNEL_PAIRS];
				uniform float gaussianWeights[KERNEL_PAIRS];

				void main() {

					vec3 diffuseSum = texture2D( colorTexture, vUv ).rgb * centerWeight;

					for ( int i = 0; i < KERNEL_PAIRS; i ++ ) {

						vec2 uvOffset = direction * invSize * gaussianOffsets[ i ];
						vec3 sample1 = texture2D( colorTexture, vUv + uvOffset ).rgb;
						vec3 sample2 = texture2D( colorTexture, vUv - uvOffset ).rgb;
						diffuseSum += ( sample1 + sample2 ) * gaussianWeights[ i ];

					}

					gl_FragColor = vec4( diffuseSum, 1.0 );

				}`})}_getCompositeMaterial(e){return new Bt({defines:{NUM_MIPS:e},uniforms:{blurTexture1:{value:null},blurTexture2:{value:null},blurTexture3:{value:null},blurTexture4:{value:null},blurTexture5:{value:null},bloomStrength:{value:1},bloomFactors:{value:null},bloomTintColors:{value:null},bloomRadius:{value:0}},vertexShader:`

				varying vec2 vUv;

				void main() {

					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

				}`,fragmentShader:`

				varying vec2 vUv;

				uniform sampler2D blurTexture1;
				uniform sampler2D blurTexture2;
				uniform sampler2D blurTexture3;
				uniform sampler2D blurTexture4;
				uniform sampler2D blurTexture5;
				uniform float bloomStrength;
				uniform float bloomRadius;
				uniform float bloomFactors[NUM_MIPS];
				uniform vec3 bloomTintColors[NUM_MIPS];

				float lerpBloomFactor( const in float factor ) {

					float mirrorFactor = 1.2 - factor;
					return mix( factor, mirrorFactor, bloomRadius );

				}

				void main() {

					// 3.0 for backwards compatibility with previous alpha-based intensity
					vec3 bloom = 3.0 * bloomStrength * (
						lerpBloomFactor( bloomFactors[ 0 ] ) * bloomTintColors[ 0 ] * texture2D( blurTexture1, vUv ).rgb +
						lerpBloomFactor( bloomFactors[ 1 ] ) * bloomTintColors[ 1 ] * texture2D( blurTexture2, vUv ).rgb +
						lerpBloomFactor( bloomFactors[ 2 ] ) * bloomTintColors[ 2 ] * texture2D( blurTexture3, vUv ).rgb +
						lerpBloomFactor( bloomFactors[ 3 ] ) * bloomTintColors[ 3 ] * texture2D( blurTexture4, vUv ).rgb +
						lerpBloomFactor( bloomFactors[ 4 ] ) * bloomTintColors[ 4 ] * texture2D( blurTexture5, vUv ).rgb
					);

					float bloomAlpha = max( bloom.r, max( bloom.g, bloom.b ) );
					gl_FragColor = vec4( bloom, bloomAlpha );

				}`})}};Gr.BlurDirectionX=new ne(1,0);Gr.BlurDirectionY=new ne(0,1);var no={name:"OutputShader",uniforms:{tDiffuse:{value:null},toneMappingExposure:{value:1}},vertexShader:`
		precision highp float;

		uniform mat4 modelViewMatrix;
		uniform mat4 projectionMatrix;

		attribute vec3 position;
		attribute vec2 uv;

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		precision highp float;

		uniform sampler2D tDiffuse;

		#include <tonemapping_pars_fragment>
		#include <colorspace_pars_fragment>

		varying vec2 vUv;

		void main() {

			gl_FragColor = texture2D( tDiffuse, vUv );

			// tone mapping

			#ifdef LINEAR_TONE_MAPPING

				gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );

			#elif defined( REINHARD_TONE_MAPPING )

				gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );

			#elif defined( CINEON_TONE_MAPPING )

				gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );

			#elif defined( ACES_FILMIC_TONE_MAPPING )

				gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );

			#elif defined( AGX_TONE_MAPPING )

				gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );

			#elif defined( NEUTRAL_TONE_MAPPING )

				gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );

			#elif defined( CUSTOM_TONE_MAPPING )

				gl_FragColor.rgb = CustomToneMapping( gl_FragColor.rgb );

			#endif

			// color space

			#ifdef SRGB_TRANSFER

				gl_FragColor = sRGBTransferOETF( gl_FragColor );

			#endif

		}`};var Rc=class extends Fn{constructor(){super(),this.isOutputPass=!0,this.uniforms=qi.clone(no.uniforms),this.material=new Ar({name:no.name,uniforms:this.uniforms,vertexShader:no.vertexShader,fragmentShader:no.fragmentShader}),this._fsQuad=new ms(this.material),this._outputColorSpace=null,this._toneMapping=null}render(e,t,n){this.uniforms.tDiffuse.value=n.texture,this.uniforms.toneMappingExposure.value=e.toneMappingExposure,(this._outputColorSpace!==e.outputColorSpace||this._toneMapping!==e.toneMapping)&&(this._outputColorSpace=e.outputColorSpace,this._toneMapping=e.toneMapping,this.material.defines={},it.getTransfer(this._outputColorSpace)===_t&&(this.material.defines.SRGB_TRANSFER=""),this._toneMapping===Oa?this.material.defines.LINEAR_TONE_MAPPING="":this._toneMapping===Ba?this.material.defines.REINHARD_TONE_MAPPING="":this._toneMapping===ka?this.material.defines.CINEON_TONE_MAPPING="":this._toneMapping===Fs?this.material.defines.ACES_FILMIC_TONE_MAPPING="":this._toneMapping===Ga?this.material.defines.AGX_TONE_MAPPING="":this._toneMapping===Va?this.material.defines.NEUTRAL_TONE_MAPPING="":this._toneMapping===za&&(this.material.defines.CUSTOM_TONE_MAPPING=""),this.material.needsUpdate=!0),this.renderToScreen===!0?(e.setRenderTarget(null),this._fsQuad.render(e)):(e.setRenderTarget(t),this.clear&&e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil),this._fsQuad.render(e))}dispose(){this.material.dispose(),this._fsQuad.dispose()}};function Cu(s,e){if(e===$h)return console.warn("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Geometry already defined as triangles."),s;if(e===Ur||e===Ja){let t=s.getIndex();if(t===null){let r=[],a=s.getAttribute("position");if(a!==void 0){for(let o=0;o<a.count;o++)r.push(o);s.setIndex(r),t=s.getIndex()}else return console.error("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Undefined position attribute. Processing not possible."),s}let n=t.count-2,i=[];if(e===Ur)for(let r=1;r<=n;r++)i.push(t.getX(0)),i.push(t.getX(r)),i.push(t.getX(r+1));else for(let r=0;r<n;r++)r%2===0?(i.push(t.getX(r)),i.push(t.getX(r+1)),i.push(t.getX(r+2))):(i.push(t.getX(r+2)),i.push(t.getX(r+1)),i.push(t.getX(r)));return i.length/3!==n&&console.error("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Unable to generate correct amount of triangles."),s.setIndex(i),s.clearGroups(),s}else return console.error("THREE.BufferGeometryUtils.toTrianglesDrawMode(): Unknown draw mode:",e),s}function rm(s){let e=new Map,t=new Map,n=s.clone();return am(s,n,function(i,r){e.set(r,i),t.set(i,r)}),n.traverse(function(i){if(!i.isSkinnedMesh)return;let r=i,a=e.get(i),o=a.skeleton.bones;r.skeleton=a.skeleton.clone(),r.bindMatrix.copy(a.bindMatrix),r.skeleton.bones=o.map(function(c){return t.get(c)}),r.bind(r.skeleton,r.bindMatrix)}),n}function am(s,e,t){t(s,e);for(let n=0;n<s.children.length;n++)am(s.children[n],e.children[n],t)}var Ic=class extends bi{constructor(e){super(e),this.dracoLoader=null,this.ktx2Loader=null,this.meshoptDecoder=null,this.pluginCallbacks=[],this.register(function(t){return new Uu(t)}),this.register(function(t){return new Fu(t)}),this.register(function(t){return new Xu(t)}),this.register(function(t){return new qu(t)}),this.register(function(t){return new Yu(t)}),this.register(function(t){return new Bu(t)}),this.register(function(t){return new ku(t)}),this.register(function(t){return new zu(t)}),this.register(function(t){return new Gu(t)}),this.register(function(t){return new Du(t)}),this.register(function(t){return new Vu(t)}),this.register(function(t){return new Ou(t)}),this.register(function(t){return new Wu(t)}),this.register(function(t){return new Hu(t)}),this.register(function(t){return new Lu(t)}),this.register(function(t){return new Pc(t,lt.EXT_MESHOPT_COMPRESSION)}),this.register(function(t){return new Pc(t,lt.KHR_MESHOPT_COMPRESSION)}),this.register(function(t){return new Ku(t)})}load(e,t,n,i){let r=this,a;if(this.resourcePath!=="")a=this.resourcePath;else if(this.path!==""){let l=Wi.extractUrlBase(e);a=Wi.resolveURL(l,this.path)}else a=Wi.extractUrlBase(e);this.manager.itemStart(e);let o=function(l){i?i(l):console.error(l),r.manager.itemError(e),r.manager.itemEnd(e)},c=new Er(this.manager);c.setPath(this.path),c.setResponseType("arraybuffer"),c.setRequestHeader(this.requestHeader),c.setWithCredentials(this.withCredentials),c.load(e,function(l){try{r.parse(l,a,function(h){t(h),r.manager.itemEnd(e)},o)}catch(h){o(h)}},n,o)}setDRACOLoader(e){return this.dracoLoader=e,this}setKTX2Loader(e){return this.ktx2Loader=e,this}setMeshoptDecoder(e){return this.meshoptDecoder=e,this}register(e){return this.pluginCallbacks.indexOf(e)===-1&&this.pluginCallbacks.push(e),this}unregister(e){return this.pluginCallbacks.indexOf(e)!==-1&&this.pluginCallbacks.splice(this.pluginCallbacks.indexOf(e),1),this}parse(e,t,n,i){let r,a={},o={},c=new TextDecoder;if(typeof e=="string")r=JSON.parse(e);else if(e instanceof ArrayBuffer)if(c.decode(new Uint8Array(e,0,4))===um){try{a[lt.KHR_BINARY_GLTF]=new Zu(e)}catch(u){i&&i(u);return}r=JSON.parse(a[lt.KHR_BINARY_GLTF].content)}else r=JSON.parse(c.decode(e));else r=e;if(r.asset===void 0||r.asset.version[0]<2){i&&i(new Error("THREE.GLTFLoader: Unsupported asset. glTF versions >=2.0 are supported."));return}let l=new nd(r,{path:t||this.resourcePath||"",crossOrigin:this.crossOrigin,requestHeader:this.requestHeader,manager:this.manager,ktx2Loader:this.ktx2Loader,meshoptDecoder:this.meshoptDecoder});l.fileLoader.setRequestHeader(this.requestHeader);for(let h=0;h<this.pluginCallbacks.length;h++){let u=this.pluginCallbacks[h](l);u.name||console.error("THREE.GLTFLoader: Invalid plugin found: missing name"),o[u.name]=u,a[u.name]=!0}if(r.extensionsUsed)for(let h=0;h<r.extensionsUsed.length;++h){let u=r.extensionsUsed[h],d=r.extensionsRequired||[];switch(u){case lt.KHR_MATERIALS_UNLIT:a[u]=new Nu;break;case lt.KHR_DRACO_MESH_COMPRESSION:a[u]=new Ju(r,this.dracoLoader);break;case lt.KHR_TEXTURE_TRANSFORM:a[u]=new $u;break;case lt.KHR_MESH_QUANTIZATION:a[u]=new ju;break;default:d.indexOf(u)>=0&&o[u]===void 0&&console.warn('THREE.GLTFLoader: Unknown extension "'+u+'".')}}l.setExtensions(a),l.setPlugins(o),l.parse(n,i)}parseAsync(e,t){let n=this;return new Promise(function(i,r){n.parse(e,t,i,r)})}};function aM(){let s={};return{get:function(e){return s[e]},add:function(e,t){s[e]=t},remove:function(e){delete s[e]},removeAll:function(){s={}}}}function Yt(s,e,t){let n=s.json.materials[e];return n.extensions&&n.extensions[t]?n.extensions[t]:null}var lt={KHR_BINARY_GLTF:"KHR_binary_glTF",KHR_DRACO_MESH_COMPRESSION:"KHR_draco_mesh_compression",KHR_LIGHTS_PUNCTUAL:"KHR_lights_punctual",KHR_MATERIALS_CLEARCOAT:"KHR_materials_clearcoat",KHR_MATERIALS_DISPERSION:"KHR_materials_dispersion",KHR_MATERIALS_IOR:"KHR_materials_ior",KHR_MATERIALS_SHEEN:"KHR_materials_sheen",KHR_MATERIALS_SPECULAR:"KHR_materials_specular",KHR_MATERIALS_TRANSMISSION:"KHR_materials_transmission",KHR_MATERIALS_IRIDESCENCE:"KHR_materials_iridescence",KHR_MATERIALS_ANISOTROPY:"KHR_materials_anisotropy",KHR_MATERIALS_UNLIT:"KHR_materials_unlit",KHR_MATERIALS_VOLUME:"KHR_materials_volume",KHR_TEXTURE_BASISU:"KHR_texture_basisu",KHR_TEXTURE_TRANSFORM:"KHR_texture_transform",KHR_MESH_QUANTIZATION:"KHR_mesh_quantization",KHR_MATERIALS_EMISSIVE_STRENGTH:"KHR_materials_emissive_strength",EXT_MATERIALS_BUMP:"EXT_materials_bump",EXT_TEXTURE_WEBP:"EXT_texture_webp",EXT_TEXTURE_AVIF:"EXT_texture_avif",EXT_MESHOPT_COMPRESSION:"EXT_meshopt_compression",KHR_MESHOPT_COMPRESSION:"KHR_meshopt_compression",EXT_MESH_GPU_INSTANCING:"EXT_mesh_gpu_instancing"},Lu=class{constructor(e){this.parser=e,this.name=lt.KHR_LIGHTS_PUNCTUAL,this.cache={refs:{},uses:{}}}_markDefs(){let e=this.parser,t=this.parser.json.nodes||[];for(let n=0,i=t.length;n<i;n++){let r=t[n];r.extensions&&r.extensions[this.name]&&r.extensions[this.name].light!==void 0&&e._addNodeRef(this.cache,r.extensions[this.name].light)}}_loadLight(e){let t=this.parser,n="light:"+e,i=t.cache.get(n);if(i)return i;let r=t.json,c=((r.extensions&&r.extensions[this.name]||{}).lights||[])[e],l,h=new Me(16777215);c.color!==void 0&&h.setRGB(c.color[0],c.color[1],c.color[2],gn);let u=c.range!==void 0?c.range:0;switch(c.type){case"directional":l=new Nn(h),l.target.position.set(0,0,-1),l.add(l.target);break;case"point":l=new Ln(h),l.distance=u;break;case"spot":l=new Da(h),l.distance=u,c.spot=c.spot||{},c.spot.innerConeAngle=c.spot.innerConeAngle!==void 0?c.spot.innerConeAngle:0,c.spot.outerConeAngle=c.spot.outerConeAngle!==void 0?c.spot.outerConeAngle:Math.PI/4,l.angle=c.spot.outerConeAngle,l.penumbra=1-c.spot.innerConeAngle/c.spot.outerConeAngle,l.target.position.set(0,0,-1),l.add(l.target);break;default:throw new Error("THREE.GLTFLoader: Unexpected light type: "+c.type)}return l.position.set(0,0,0),Ri(l,c),c.intensity!==void 0&&(l.intensity=c.intensity),l.name=t.createUniqueName(c.name||"light_"+e),i=Promise.resolve(l),t.cache.add(n,i),i}getDependency(e,t){if(e==="light")return this._loadLight(t)}createNodeAttachment(e){let t=this,n=this.parser,r=n.json.nodes[e],o=(r.extensions&&r.extensions[this.name]||{}).light;return o===void 0?null:this._loadLight(o).then(function(c){return n._getNodeRef(t.cache,o,c)})}},Nu=class{constructor(){this.name=lt.KHR_MATERIALS_UNLIT}getMaterialType(){return Ye}extendParams(e,t,n){let i=[];e.color=new Me(1,1,1),e.opacity=1;let r=t.pbrMetallicRoughness;if(r){if(Array.isArray(r.baseColorFactor)){let a=r.baseColorFactor;e.color.setRGB(a[0],a[1],a[2],gn),e.opacity=a[3]}r.baseColorTexture!==void 0&&i.push(n.assignTexture(e,"map",r.baseColorTexture,Ct))}return Promise.all(i)}},Du=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_EMISSIVE_STRENGTH}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);return n===null||n.emissiveStrength!==void 0&&(t.emissiveIntensity=n.emissiveStrength),Promise.resolve()}},Uu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_CLEARCOAT}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];if(n.clearcoatFactor!==void 0&&(t.clearcoat=n.clearcoatFactor),n.clearcoatTexture!==void 0&&i.push(this.parser.assignTexture(t,"clearcoatMap",n.clearcoatTexture)),n.clearcoatRoughnessFactor!==void 0&&(t.clearcoatRoughness=n.clearcoatRoughnessFactor),n.clearcoatRoughnessTexture!==void 0&&i.push(this.parser.assignTexture(t,"clearcoatRoughnessMap",n.clearcoatRoughnessTexture)),n.clearcoatNormalTexture!==void 0&&(i.push(this.parser.assignTexture(t,"clearcoatNormalMap",n.clearcoatNormalTexture)),n.clearcoatNormalTexture.scale!==void 0)){let r=n.clearcoatNormalTexture.scale;t.clearcoatNormalScale=new ne(r,r)}return Promise.all(i)}},Fu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_DISPERSION}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);return n===null||(t.dispersion=n.dispersion!==void 0?n.dispersion:0),Promise.resolve()}},Ou=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_IRIDESCENCE}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];return n.iridescenceFactor!==void 0&&(t.iridescence=n.iridescenceFactor),n.iridescenceTexture!==void 0&&i.push(this.parser.assignTexture(t,"iridescenceMap",n.iridescenceTexture)),n.iridescenceIor!==void 0&&(t.iridescenceIOR=n.iridescenceIor),t.iridescenceThicknessRange===void 0&&(t.iridescenceThicknessRange=[100,400]),n.iridescenceThicknessMinimum!==void 0&&(t.iridescenceThicknessRange[0]=n.iridescenceThicknessMinimum),n.iridescenceThicknessMaximum!==void 0&&(t.iridescenceThicknessRange[1]=n.iridescenceThicknessMaximum),n.iridescenceThicknessTexture!==void 0&&i.push(this.parser.assignTexture(t,"iridescenceThicknessMap",n.iridescenceThicknessTexture)),Promise.all(i)}},Bu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_SHEEN}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];if(t.sheenColor=new Me(0,0,0),t.sheenRoughness=0,t.sheen=1,n.sheenColorFactor!==void 0){let r=n.sheenColorFactor;t.sheenColor.setRGB(r[0],r[1],r[2],gn)}return n.sheenRoughnessFactor!==void 0&&(t.sheenRoughness=n.sheenRoughnessFactor),n.sheenColorTexture!==void 0&&i.push(this.parser.assignTexture(t,"sheenColorMap",n.sheenColorTexture,Ct)),n.sheenRoughnessTexture!==void 0&&i.push(this.parser.assignTexture(t,"sheenRoughnessMap",n.sheenRoughnessTexture)),Promise.all(i)}},ku=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_TRANSMISSION}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];return n.transmissionFactor!==void 0&&(t.transmission=n.transmissionFactor),n.transmissionTexture!==void 0&&i.push(this.parser.assignTexture(t,"transmissionMap",n.transmissionTexture)),Promise.all(i)}},zu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_VOLUME}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];t.thickness=n.thicknessFactor!==void 0?n.thicknessFactor:0,n.thicknessTexture!==void 0&&i.push(this.parser.assignTexture(t,"thicknessMap",n.thicknessTexture)),t.attenuationDistance=n.attenuationDistance||1/0;let r=n.attenuationColor||[1,1,1];return t.attenuationColor=new Me().setRGB(r[0],r[1],r[2],gn),Promise.all(i)}},Gu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_IOR}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);return n===null||(t.ior=n.ior!==void 0?n.ior:1.5,t.ior===0&&(t.ior=1e3)),Promise.resolve()}},Vu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_SPECULAR}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];t.specularIntensity=n.specularFactor!==void 0?n.specularFactor:1,n.specularTexture!==void 0&&i.push(this.parser.assignTexture(t,"specularIntensityMap",n.specularTexture));let r=n.specularColorFactor||[1,1,1];return t.specularColor=new Me().setRGB(r[0],r[1],r[2],gn),n.specularColorTexture!==void 0&&i.push(this.parser.assignTexture(t,"specularColorMap",n.specularColorTexture,Ct)),Promise.all(i)}},Hu=class{constructor(e){this.parser=e,this.name=lt.EXT_MATERIALS_BUMP}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];return t.bumpScale=n.bumpFactor!==void 0?n.bumpFactor:1,n.bumpTexture!==void 0&&i.push(this.parser.assignTexture(t,"bumpMap",n.bumpTexture)),Promise.all(i)}},Wu=class{constructor(e){this.parser=e,this.name=lt.KHR_MATERIALS_ANISOTROPY}getMaterialType(e){return Yt(this.parser,e,this.name)!==null?It:null}extendMaterialParams(e,t){let n=Yt(this.parser,e,this.name);if(n===null)return Promise.resolve();let i=[];return n.anisotropyStrength!==void 0&&(t.anisotropy=n.anisotropyStrength),n.anisotropyRotation!==void 0&&(t.anisotropyRotation=n.anisotropyRotation),n.anisotropyTexture!==void 0&&i.push(this.parser.assignTexture(t,"anisotropyMap",n.anisotropyTexture)),Promise.all(i)}},Xu=class{constructor(e){this.parser=e,this.name=lt.KHR_TEXTURE_BASISU}loadTexture(e){let t=this.parser,n=t.json,i=n.textures[e];if(!i.extensions||!i.extensions[this.name])return null;let r=i.extensions[this.name],a=t.options.ktx2Loader;if(!a){if(n.extensionsRequired&&n.extensionsRequired.indexOf(this.name)>=0)throw new Error("THREE.GLTFLoader: setKTX2Loader must be called before loading KTX2 textures");return null}return t.loadTextureImage(e,r.source,a)}},qu=class{constructor(e){this.parser=e,this.name=lt.EXT_TEXTURE_WEBP}loadTexture(e){let t=this.name,n=this.parser,i=n.json,r=i.textures[e];if(!r.extensions||!r.extensions[t])return null;let a=r.extensions[t],o=i.images[a.source],c=n.textureLoader;if(o.uri){let l=n.options.manager.getHandler(o.uri);l!==null&&(c=l)}return n.loadTextureImage(e,a.source,c)}},Yu=class{constructor(e){this.parser=e,this.name=lt.EXT_TEXTURE_AVIF}loadTexture(e){let t=this.name,n=this.parser,i=n.json,r=i.textures[e];if(!r.extensions||!r.extensions[t])return null;let a=r.extensions[t],o=i.images[a.source],c=n.textureLoader;if(o.uri){let l=n.options.manager.getHandler(o.uri);l!==null&&(c=l)}return n.loadTextureImage(e,a.source,c)}},Pc=class{constructor(e,t){this.name=t,this.parser=e}loadBufferView(e){let t=this.parser.json,n=t.bufferViews[e];if(n.extensions&&n.extensions[this.name]){let i=n.extensions[this.name],r=this.parser.getDependency("buffer",i.buffer),a=this.parser.options.meshoptDecoder;if(!a||!a.supported){if(t.extensionsRequired&&t.extensionsRequired.indexOf(this.name)>=0)throw new Error("THREE.GLTFLoader: setMeshoptDecoder must be called before loading compressed files");return null}return r.then(function(o){let c=i.byteOffset||0,l=i.byteLength||0,h=i.count,u=i.byteStride,d=new Uint8Array(o,c,l);return a.decodeGltfBufferAsync?a.decodeGltfBufferAsync(h,u,d,i.mode,i.filter).then(function(p){return p.buffer}):a.ready.then(function(){let p=new ArrayBuffer(h*u);return a.decodeGltfBuffer(new Uint8Array(p),h,u,d,i.mode,i.filter),p})})}else return null}},Ku=class{constructor(e){this.name=lt.EXT_MESH_GPU_INSTANCING,this.parser=e}createNodeMesh(e){let t=this.parser.json,n=t.nodes[e];if(!n.extensions||!n.extensions[this.name]||n.mesh===void 0)return null;let i=t.meshes[n.mesh];for(let l of i.primitives)if(l.mode!==Yn.TRIANGLES&&l.mode!==Yn.TRIANGLE_STRIP&&l.mode!==Yn.TRIANGLE_FAN&&l.mode!==void 0)return null;let a=n.extensions[this.name].attributes,o=[],c={};for(let l in a)o.push(this.parser.getDependency("accessor",a[l]).then(h=>(c[l]=h,c[l])));return o.length<1?null:(o.push(this.parser.createNodeMesh(e)),Promise.all(o).then(l=>{let h=l.pop(),u=h.isGroup?h.children:[h],d=l[0].count,p=[];for(let g of u){let v=new je,f=new R,m=new nn,_=new R(1,1,1),b=new un(g.geometry,g.material,d);for(let T=0;T<d;T++)c.TRANSLATION&&f.fromBufferAttribute(c.TRANSLATION,T),c.ROTATION&&m.fromBufferAttribute(c.ROTATION,T),c.SCALE&&_.fromBufferAttribute(c.SCALE,T),b.setMatrixAt(T,v.compose(f,m,_));let x=null;for(let T in c)if(T==="_COLOR_0"){let S=c[T];b.instanceColor=new Bi(S.array,S.itemSize,S.normalized)}else if(T!=="TRANSLATION"&&T!=="ROTATION"&&T!=="SCALE"){if(x===null){let A=b.geometry;x=new tt,x.name=A.name;for(let y in A.attributes)x.setAttribute(y,A.attributes[y]);for(let y in A.morphAttributes)x.morphAttributes[y]=A.morphAttributes[y];A.index!==null&&x.setIndex(A.index),x.morphTargetsRelative=A.morphTargetsRelative;for(let y of A.groups)x.addGroup(y.start,y.count,y.materialIndex);A.boundingBox!==null&&(x.boundingBox=A.boundingBox.clone()),A.boundingSphere!==null&&(x.boundingSphere=A.boundingSphere.clone()),x.drawRange.start=A.drawRange.start,x.drawRange.count=A.drawRange.count,x.userData=Object.assign({},A.userData),b.geometry=x}let S=c[T];x.setAttribute(T,new Bi(S.array,S.itemSize,S.normalized))}ft.prototype.copy.call(b,g),this.parser.assignFinalMaterial(b),p.push(b)}return h.isGroup?(h.clear(),h.add(...p),h):p[0]}))}},um="glTF",io=12,om={JSON:1313821514,BIN:5130562},Zu=class{constructor(e){this.name=lt.KHR_BINARY_GLTF,this.content=null,this.body=null;let t=new DataView(e,0,io),n=new TextDecoder;if(this.header={magic:n.decode(new Uint8Array(e.slice(0,4))),version:t.getUint32(4,!0),length:t.getUint32(8,!0)},this.header.magic!==um)throw new Error("THREE.GLTFLoader: Unsupported glTF-Binary header.");if(this.header.version<2)throw new Error("THREE.GLTFLoader: Legacy binary file detected.");let i=this.header.length-io,r=new DataView(e,io),a=0;for(;a<i;){let o=r.getUint32(a,!0);a+=4;let c=r.getUint32(a,!0);if(a+=4,c===om.JSON){let l=new Uint8Array(e,io+a,o);this.content=n.decode(l)}else if(c===om.BIN){let l=io+a;this.body=e.slice(l,l+o)}a+=o}if(this.content===null)throw new Error("THREE.GLTFLoader: JSON content not found.")}},Ju=class{constructor(e,t){if(!t)throw new Error("THREE.GLTFLoader: No DRACOLoader instance provided.");this.name=lt.KHR_DRACO_MESH_COMPRESSION,this.json=e,this.dracoLoader=t,this.dracoLoader.preload()}decodePrimitive(e,t){let n=this.json,i=this.dracoLoader,r=e.extensions[this.name].bufferView,a=e.extensions[this.name].attributes,o={},c={},l={};for(let h in a){let u=ed[h]||h.toLowerCase();o[u]=a[h]}for(let h in e.attributes){let u=ed[h]||h.toLowerCase();if(a[h]!==void 0){let d=n.accessors[e.attributes[h]],p=Vr[d.componentType];l[u]=p.name,c[u]=d.normalized===!0}}return t.getDependency("bufferView",r).then(function(h){return new Promise(function(u,d){i.decodeDracoFile(h,function(p){for(let g in p.attributes){let v=p.attributes[g],f=c[g];f!==void 0&&(v.normalized=f)}u(p)},o,l,gn,d)})})}},$u=class{constructor(){this.name=lt.KHR_TEXTURE_TRANSFORM}extendTexture(e,t){if((t.texCoord===void 0||t.texCoord===e.channel)&&t.offset===void 0&&t.rotation===void 0&&t.scale===void 0)return e;if(e=e.clone(),t.texCoord!==void 0&&(e.channel=t.texCoord),t.offset!==void 0&&e.offset.fromArray(t.offset),t.rotation!==void 0&&(e.rotation=t.rotation),t.scale!==void 0&&e.repeat.fromArray(t.scale),t.rotation!==void 0){let n=Math.cos(e.rotation),i=Math.sin(e.rotation);e.matrix.set(e.repeat.x*n,e.repeat.y*i,e.offset.x,-e.repeat.x*i,e.repeat.y*n,e.offset.y,0,0,1),e.matrixAutoUpdate=!1}return e.needsUpdate=!0,e}},ju=class{constructor(){this.name=lt.KHR_MESH_QUANTIZATION}},Lc=class extends Si{constructor(e,t,n,i){super(e,t,n,i)}copySampleValue_(e){let t=this.resultBuffer,n=this.sampleValues,i=this.valueSize,r=e*i*3+i;for(let a=0;a!==i;a++)t[a]=n[r+a];return t}interpolate_(e,t,n,i){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=o*2,l=o*3,h=i-t,u=(n-t)/h,d=u*u,p=d*u,g=e*l,v=g-l,f=-2*p+3*d,m=p-d,_=1-f,b=m-d+u;for(let x=0;x!==o;x++){let T=a[v+x+o],S=a[v+x+c]*h,A=a[g+x+o],y=a[g+x]*h;r[x]=_*T+b*S+f*A+m*y}return r}},oM=new nn,Qu=class extends Lc{interpolate_(e,t,n,i){let r=super.interpolate_(e,t,n,i);return oM.fromArray(r).normalize().toArray(r),r}},Yn={FLOAT:5126,FLOAT_MAT3:35675,FLOAT_MAT4:35676,FLOAT_VEC2:35664,FLOAT_VEC3:35665,FLOAT_VEC4:35666,LINEAR:9729,REPEAT:10497,SAMPLER_2D:35678,POINTS:0,LINES:1,LINE_LOOP:2,LINE_STRIP:3,TRIANGLES:4,TRIANGLE_STRIP:5,TRIANGLE_FAN:6,UNSIGNED_BYTE:5121,UNSIGNED_SHORT:5123},Vr={5120:Int8Array,5121:Uint8Array,5122:Int16Array,5123:Uint16Array,5125:Uint32Array,5126:Float32Array},lm={9728:Wt,9729:Xt,9984:bl,9985:Lr,9986:Bs,9987:ai},cm={33071:rn,33648:mr,10497:_i},Ru={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT2:4,MAT3:9,MAT4:16},ed={POSITION:"position",NORMAL:"normal",TANGENT:"tangent",TEXCOORD_0:"uv",TEXCOORD_1:"uv1",TEXCOORD_2:"uv2",TEXCOORD_3:"uv3",COLOR_0:"color",WEIGHTS_0:"skinWeight",JOINTS_0:"skinIndex"},gs={scale:"scale",translation:"position",rotation:"quaternion",weights:"morphTargetInfluences"},lM={CUBICSPLINE:void 0,LINEAR:ws,STEP:Ts},Iu={OPAQUE:"OPAQUE",MASK:"MASK",BLEND:"BLEND"};function cM(s){return s.DefaultMaterial===void 0&&(s.DefaultMaterial=new nt({color:16777215,emissive:0,metalness:1,roughness:1,transparent:!1,depthTest:!0,side:wi})),s.DefaultMaterial}function Vs(s,e,t){for(let n in t.extensions)s[n]===void 0&&(e.userData.gltfExtensions=e.userData.gltfExtensions||{},e.userData.gltfExtensions[n]=t.extensions[n])}function Ri(s,e){e.extras!==void 0&&(typeof e.extras=="object"?Object.assign(s.userData,e.extras):console.warn("THREE.GLTFLoader: Ignoring primitive type .extras, "+e.extras))}function hM(s,e,t){let n=!1,i=!1,r=!1;for(let l=0,h=e.length;l<h;l++){let u=e[l];if(u.POSITION!==void 0&&(n=!0),u.NORMAL!==void 0&&(i=!0),u.COLOR_0!==void 0&&(r=!0),n&&i&&r)break}if(!n&&!i&&!r)return Promise.resolve(s);let a=[],o=[],c=[];for(let l=0,h=e.length;l<h;l++){let u=e[l];if(n){let d=u.POSITION!==void 0?t.getDependency("accessor",u.POSITION):s.attributes.position;a.push(d)}if(i){let d=u.NORMAL!==void 0?t.getDependency("accessor",u.NORMAL):s.attributes.normal;o.push(d)}if(r){let d=u.COLOR_0!==void 0?t.getDependency("accessor",u.COLOR_0):s.attributes.color;c.push(d)}}return Promise.all([Promise.all(a),Promise.all(o),Promise.all(c)]).then(function(l){let h=l[0],u=l[1],d=l[2];return n&&(s.morphAttributes.position=h),i&&(s.morphAttributes.normal=u),r&&(s.morphAttributes.color=d),s.morphTargetsRelative=!0,s})}function uM(s,e){if(s.updateMorphTargets(),e.weights!==void 0)for(let t=0,n=e.weights.length;t<n;t++)s.morphTargetInfluences[t]=e.weights[t];if(e.extras&&Array.isArray(e.extras.targetNames)){let t=e.extras.targetNames;if(s.morphTargetInfluences.length===t.length){s.morphTargetDictionary={};for(let n=0,i=t.length;n<i;n++)s.morphTargetDictionary[t[n]]=n}else console.warn("THREE.GLTFLoader: Invalid extras.targetNames length. Ignoring names.")}}function dM(s){let e,t=s.extensions&&s.extensions[lt.KHR_DRACO_MESH_COMPRESSION];if(t?e="draco:"+t.bufferView+":"+t.indices+":"+Pu(t.attributes):e=s.indices+":"+Pu(s.attributes)+":"+s.mode,s.targets!==void 0)for(let n=0,i=s.targets.length;n<i;n++)e+=":"+Pu(s.targets[n]);return e}function Pu(s){let e="",t=Object.keys(s).sort();for(let n=0,i=t.length;n<i;n++)e+=t[n]+":"+s[t[n]]+";";return e}function td(s){switch(s){case Int8Array:return 1/127;case Uint8Array:return 1/255;case Int16Array:return 1/32767;case Uint16Array:return 1/65535;default:throw new Error("THREE.GLTFLoader: Unsupported normalized accessor component type.")}}function fM(s){return s.search(/\.jpe?g($|\?)/i)>0||s.search(/^data\:image\/jpeg/)===0?"image/jpeg":s.search(/\.webp($|\?)/i)>0||s.search(/^data\:image\/webp/)===0?"image/webp":s.search(/\.ktx2($|\?)/i)>0||s.search(/^data\:image\/ktx2/)===0?"image/ktx2":"image/png"}var pM=new je,nd=class{constructor(e={},t={}){this.json=e,this.extensions={},this.plugins={},this.options=t,this.cache=new aM,this.associations=new Map,this.primitiveCache={},this.nodeCache={},this.meshCache={refs:{},uses:{}},this.cameraCache={refs:{},uses:{}},this.lightCache={refs:{},uses:{}},this.sourceCache={},this.textureCache={},this.nodeNamesUsed={};let n=!1,i=-1,r=!1,a=-1;if(typeof navigator<"u"&&typeof navigator.userAgent<"u"){let o=navigator.userAgent;n=/^((?!chrome|android).)*safari/i.test(o)===!0;let c=o.match(/Version\/(\d+)/);i=n&&c?parseInt(c[1],10):-1,r=o.indexOf("Firefox")>-1,a=r?o.match(/Firefox\/([0-9]+)\./)[1]:-1}typeof createImageBitmap>"u"||n&&i<17||r&&a<98?this.textureLoader=new Ls(this.options.manager):this.textureLoader=new Ua(this.options.manager),this.textureLoader.setCrossOrigin(this.options.crossOrigin),this.textureLoader.setRequestHeader(this.options.requestHeader),this.fileLoader=new Er(this.options.manager),this.fileLoader.setResponseType("arraybuffer"),this.options.crossOrigin==="use-credentials"&&this.fileLoader.setWithCredentials(!0)}setExtensions(e){this.extensions=e}setPlugins(e){this.plugins=e}parse(e,t){let n=this,i=this.json,r=this.extensions;this.cache.removeAll(),this.nodeCache={},this._invokeAll(function(a){return a._markDefs&&a._markDefs()}),Promise.all(this._invokeAll(function(a){return a.beforeRoot&&a.beforeRoot()})).then(function(){return Promise.all([n.getDependencies("scene"),n.getDependencies("animation"),n.getDependencies("camera")])}).then(function(a){let o={scene:a[0][i.scene||0],scenes:a[0],animations:a[1],cameras:a[2],asset:i.asset,parser:n,userData:{}};return Vs(r,o,i),Ri(o,i),Promise.all(n._invokeAll(function(c){return c.afterRoot&&c.afterRoot(o)})).then(function(){for(let c of o.scenes)c.updateMatrixWorld();e(o)})}).catch(t)}_markDefs(){let e=this.json.nodes||[],t=this.json.skins||[],n=this.json.meshes||[];for(let i=0,r=t.length;i<r;i++){let a=t[i].joints;for(let o=0,c=a.length;o<c;o++)e[a[o]].isBone=!0}for(let i=0,r=e.length;i<r;i++){let a=e[i];a.mesh!==void 0&&(this._addNodeRef(this.meshCache,a.mesh),a.skin!==void 0&&(n[a.mesh].isSkinnedMesh=!0)),a.camera!==void 0&&this._addNodeRef(this.cameraCache,a.camera)}}_addNodeRef(e,t){t!==void 0&&(e.refs[t]===void 0&&(e.refs[t]=e.uses[t]=0),e.refs[t]++)}_getNodeRef(e,t,n){if(e.refs[t]<=1)return n;let i=n.clone(),r=(a,o)=>{let c=this.associations.get(a);c!=null&&this.associations.set(o,c);for(let[l,h]of a.children.entries())r(h,o.children[l])};return r(n,i),i.name+="_instance_"+e.uses[t]++,i}_invokeOne(e){let t=Object.values(this.plugins);t.push(this);for(let n=0;n<t.length;n++){let i=e(t[n]);if(i)return i}return null}_invokeAll(e){let t=Object.values(this.plugins);t.unshift(this);let n=[];for(let i=0;i<t.length;i++){let r=e(t[i]);r&&n.push(r)}return n}getDependency(e,t){let n=e+":"+t,i=this.cache.get(n);if(!i){switch(e){case"scene":i=this.loadScene(t);break;case"node":i=this._invokeOne(function(r){return r.loadNode&&r.loadNode(t)});break;case"mesh":i=this._invokeOne(function(r){return r.loadMesh&&r.loadMesh(t)});break;case"accessor":i=this.loadAccessor(t);break;case"bufferView":i=this._invokeOne(function(r){return r.loadBufferView&&r.loadBufferView(t)});break;case"buffer":i=this.loadBuffer(t);break;case"material":i=this._invokeOne(function(r){return r.loadMaterial&&r.loadMaterial(t)});break;case"texture":i=this._invokeOne(function(r){return r.loadTexture&&r.loadTexture(t)});break;case"skin":i=this.loadSkin(t);break;case"animation":i=this._invokeOne(function(r){return r.loadAnimation&&r.loadAnimation(t)});break;case"camera":i=this.loadCamera(t);break;default:if(i=this._invokeOne(function(r){return r!=this&&r.getDependency&&r.getDependency(e,t)}),!i)throw new Error("Unknown type: "+e);break}this.cache.add(n,i)}return i}getDependencies(e){let t=this.cache.get(e);if(!t){let n=this,i=this.json[e+(e==="mesh"?"es":"s")]||[];t=Promise.all(i.map(function(r,a){return n.getDependency(e,a)})),this.cache.add(e,t)}return t}loadBuffer(e){let t=this.json.buffers[e],n=this.fileLoader;if(t.type&&t.type!=="arraybuffer")throw new Error("THREE.GLTFLoader: "+t.type+" buffer type is not supported.");if(t.uri===void 0&&e===0)return Promise.resolve(this.extensions[lt.KHR_BINARY_GLTF].body);let i=this.options;return new Promise(function(r,a){n.load(Wi.resolveURL(t.uri,i.path),r,void 0,function(){a(new Error('THREE.GLTFLoader: Failed to load buffer "'+t.uri+'".'))})})}loadBufferView(e){let t=this.json.bufferViews[e];return this.getDependency("buffer",t.buffer).then(function(n){let i=t.byteLength||0,r=t.byteOffset||0;return n.slice(r,r+i)})}loadAccessor(e){let t=this,n=this.json,i=this.json.accessors[e];if(i.bufferView===void 0&&i.sparse===void 0){let a=Ru[i.type],o=Vr[i.componentType],c=i.normalized===!0,l=new o(i.count*a);return Promise.resolve(new Ft(l,a,c))}let r=[];return i.bufferView!==void 0?r.push(this.getDependency("bufferView",i.bufferView)):r.push(null),i.sparse!==void 0&&(r.push(this.getDependency("bufferView",i.sparse.indices.bufferView)),r.push(this.getDependency("bufferView",i.sparse.values.bufferView))),Promise.all(r).then(function(a){let o=a[0],c=Ru[i.type],l=Vr[i.componentType],h=l.BYTES_PER_ELEMENT,u=h*c,d=i.byteOffset||0,p=i.bufferView!==void 0?n.bufferViews[i.bufferView].byteStride:void 0,g=i.normalized===!0,v,f;if(p&&p!==u){let m=Math.floor(d/p),_="InterleavedBuffer:"+i.bufferView+":"+i.componentType+":"+m+":"+i.count,b=t.cache.get(_);b||(v=new l(o,m*p,i.count*p/h),b=new Cs(v,p/h),t.cache.add(_,b)),f=new rs(b,c,d%p/h,g)}else o===null?v=new l(i.count*c):v=new l(o,d,i.count*c),f=new Ft(v,c,g);if(i.sparse!==void 0){let m=Ru.SCALAR,_=Vr[i.sparse.indices.componentType],b=i.sparse.indices.byteOffset||0,x=i.sparse.values.byteOffset||0,T=new _(a[1],b,i.sparse.count*m),S=new l(a[2],x,i.sparse.count*c);o!==null&&(f=new Ft(f.array.slice(),f.itemSize,f.normalized)),f.normalized=!1;for(let A=0,y=T.length;A<y;A++){let E=T[A];if(f.setX(E,S[A*c]),c>=2&&f.setY(E,S[A*c+1]),c>=3&&f.setZ(E,S[A*c+2]),c>=4&&f.setW(E,S[A*c+3]),c>=5)throw new Error("THREE.GLTFLoader: Unsupported itemSize in sparse BufferAttribute.")}f.normalized=g}return f})}loadTexture(e){let t=this.json,n=this.options,r=t.textures[e].source,a=t.images[r],o=this.textureLoader;if(a.uri){let c=n.manager.getHandler(a.uri);c!==null&&(o=c)}return this.loadTextureImage(e,r,o)}loadTextureImage(e,t,n){let i=this,r=this.json,a=r.textures[e],o=r.images[t],c=(o.uri||o.bufferView)+":"+a.sampler;if(this.textureCache[c])return this.textureCache[c];let l=this.loadImageSource(t,n).then(function(h){h.flipY=!1,h.name=a.name||o.name||"",h.name===""&&typeof o.uri=="string"&&o.uri.startsWith("data:image/")===!1&&(h.name=o.uri);let d=(r.samplers||{})[a.sampler]||{};return h.magFilter=lm[d.magFilter]||Xt,h.minFilter=lm[d.minFilter]||ai,h.wrapS=cm[d.wrapS]||_i,h.wrapT=cm[d.wrapT]||_i,h.generateMipmaps=!h.isCompressedTexture&&h.minFilter!==Wt&&h.minFilter!==Xt,i.associations.set(h,{textures:e}),h}).catch(function(){return null});return this.textureCache[c]=l,l}loadImageSource(e,t){let n=this,i=this.json,r=this.options;if(this.sourceCache[e]!==void 0)return this.sourceCache[e].then(u=>u.clone());let a=i.images[e],o=self.URL||self.webkitURL,c=a.uri||"",l=!1;if(a.bufferView!==void 0)c=n.getDependency("bufferView",a.bufferView).then(function(u){l=!0;let d=new Blob([u],{type:a.mimeType});return c=o.createObjectURL(d),c});else if(a.uri===void 0)throw new Error("THREE.GLTFLoader: Image "+e+" is missing URI and bufferView");let h=Promise.resolve(c).then(function(u){return new Promise(function(d,p){let g=d;t.isImageBitmapLoader===!0&&(g=function(v){let f=new jt(v);f.needsUpdate=!0,d(f)}),t.load(Wi.resolveURL(u,r.path),g,void 0,p)})}).then(function(u){return l===!0&&o.revokeObjectURL(c),Ri(u,a),u.userData.mimeType=a.mimeType||fM(a.uri),u}).catch(function(u){throw console.error("THREE.GLTFLoader: Couldn't load texture",c),u});return this.sourceCache[e]=h,h}assignTexture(e,t,n,i){let r=this;return this.getDependency("texture",n.index).then(function(a){if(!a)return null;if(n.texCoord!==void 0&&n.texCoord>0&&(a=a.clone(),a.channel=n.texCoord),r.extensions[lt.KHR_TEXTURE_TRANSFORM]){let o=n.extensions!==void 0?n.extensions[lt.KHR_TEXTURE_TRANSFORM]:void 0;if(o){let c=r.associations.get(a);a=r.extensions[lt.KHR_TEXTURE_TRANSFORM].extendTexture(a,o),r.associations.set(a,c)}}return i!==void 0&&(a.colorSpace=i),e[t]=a,a})}assignFinalMaterial(e){let t=e.geometry,n=e.material,i=t.attributes.tangent===void 0,r=t.attributes.color!==void 0,a=t.attributes.normal===void 0;if(e.isPoints){let o="PointsMaterial:"+n.uuid,c=this.cache.get(o);c||(c=new Rn,xn.prototype.copy.call(c,n),c.color.copy(n.color),c.map=n.map,c.sizeAttenuation=!1,this.cache.add(o,c)),n=c}else if(e.isLine){let o="LineBasicMaterial:"+n.uuid,c=this.cache.get(o);c||(c=new zn,xn.prototype.copy.call(c,n),c.color.copy(n.color),c.map=n.map,this.cache.add(o,c)),n=c}if(i||r||a){let o="ClonedMaterial:"+n.uuid+":";i&&(o+="derivative-tangents:"),r&&(o+="vertex-colors:"),a&&(o+="flat-shading:");let c=this.cache.get(o);c||(c=n.clone(),r&&(c.vertexColors=!0),a&&(c.flatShading=!0),i&&(c.normalScale&&(c.normalScale.y*=-1),c.clearcoatNormalScale&&(c.clearcoatNormalScale.y*=-1)),this.cache.add(o,c),this.associations.set(c,this.associations.get(n))),n=c}e.material=n}getMaterialType(){return nt}loadMaterial(e){let t=this,n=this.json,i=this.extensions,r=n.materials[e],a,o={},c=r.extensions||{},l=[];if(c[lt.KHR_MATERIALS_UNLIT]){let u=i[lt.KHR_MATERIALS_UNLIT];a=u.getMaterialType(),l.push(u.extendParams(o,r,t))}else{let u=r.pbrMetallicRoughness||{};if(o.color=new Me(1,1,1),o.opacity=1,Array.isArray(u.baseColorFactor)){let d=u.baseColorFactor;o.color.setRGB(d[0],d[1],d[2],gn),o.opacity=d[3]}u.baseColorTexture!==void 0&&l.push(t.assignTexture(o,"map",u.baseColorTexture,Ct)),o.metalness=u.metallicFactor!==void 0?u.metallicFactor:1,o.roughness=u.roughnessFactor!==void 0?u.roughnessFactor:1,u.metallicRoughnessTexture!==void 0&&(l.push(t.assignTexture(o,"metalnessMap",u.metallicRoughnessTexture)),l.push(t.assignTexture(o,"roughnessMap",u.metallicRoughnessTexture))),a=this._invokeOne(function(d){return d.getMaterialType&&d.getMaterialType(e)}),l.push(Promise.all(this._invokeAll(function(d){return d.extendMaterialParams&&d.extendMaterialParams(e,o)})))}r.doubleSided===!0&&(o.side=st);let h=r.alphaMode||Iu.OPAQUE;if(h===Iu.BLEND?(o.transparent=!0,o.depthWrite=!1):(o.transparent=!1,h===Iu.MASK&&(o.alphaTest=r.alphaCutoff!==void 0?r.alphaCutoff:.5)),r.normalTexture!==void 0&&a!==Ye&&(l.push(t.assignTexture(o,"normalMap",r.normalTexture)),o.normalScale=new ne(1,1),r.normalTexture.scale!==void 0)){let u=r.normalTexture.scale;o.normalScale.set(u,u)}if(r.occlusionTexture!==void 0&&a!==Ye&&(l.push(t.assignTexture(o,"aoMap",r.occlusionTexture)),r.occlusionTexture.strength!==void 0&&(o.aoMapIntensity=r.occlusionTexture.strength)),r.emissiveFactor!==void 0&&a!==Ye){let u=r.emissiveFactor;o.emissive=new Me().setRGB(u[0],u[1],u[2],gn)}return r.emissiveTexture!==void 0&&a!==Ye&&l.push(t.assignTexture(o,"emissiveMap",r.emissiveTexture,Ct)),Promise.all(l).then(function(){let u=new a(o);return r.name&&(u.name=r.name),Ri(u,r),t.associations.set(u,{materials:e}),r.extensions&&Vs(i,u,r),u})}createUniqueName(e){let t=Lt.sanitizeNodeName(e||"");return t in this.nodeNamesUsed?t+"_"+ ++this.nodeNamesUsed[t]:(this.nodeNamesUsed[t]=0,t)}loadGeometries(e){let t=this,n=this.extensions,i=this.primitiveCache;function r(o){return n[lt.KHR_DRACO_MESH_COMPRESSION].decodePrimitive(o,t).then(function(c){return hm(c,o,t)})}let a=[];for(let o=0,c=e.length;o<c;o++){let l=e[o],h=dM(l),u=i[h];if(u)a.push(u.promise);else{let d;l.extensions&&l.extensions[lt.KHR_DRACO_MESH_COMPRESSION]?d=r(l):d=hm(new tt,l,t),l.mode===Yn.TRIANGLE_STRIP?d=d.then(p=>Cu(p,Ja)):l.mode===Yn.TRIANGLE_FAN&&(d=d.then(p=>Cu(p,Ur))),i[h]={primitive:l,promise:d},a.push(d)}}return Promise.all(a)}loadMesh(e){let t=this,n=this.json,i=this.extensions,r=n.meshes[e],a=r.primitives,o=[];for(let c=0,l=a.length;c<l;c++){let h=a[c].material===void 0?cM(this.cache):this.getDependency("material",a[c].material);o.push(h)}return o.push(t.loadGeometries(a)),Promise.all(o).then(async function(c){let l=c.slice(0,c.length-1),h=c[c.length-1],u=[];for(let p=0,g=h.length;p<g;p++){let v=h[p],f=a[p],m,_=l[p];if(f.mode===Yn.TRIANGLES||f.mode===Yn.TRIANGLE_STRIP||f.mode===Yn.TRIANGLE_FAN||f.mode===void 0){let b=r.isSkinnedMesh===!0,x=v.hasAttribute("skinIndex")&&v.hasAttribute("skinWeight");b&&x===!1&&console.warn("THREE.GLTFLoader: Missing skinIndex or skinWeight attributes. Skinning disabled."),m=b&&x?new fa(v,_):new Ee(v,_),m.isSkinnedMesh===!0&&m.normalizeSkinWeights()}else if(f.mode===Yn.LINES)m=new Is(v,_);else if(f.mode===Yn.LINE_STRIP)m=new ii(v,_);else if(f.mode===Yn.LINE_LOOP)m=new ma(v,_);else if(f.mode===Yn.POINTS)m=new Gn(v,_);else throw new Error("THREE.GLTFLoader: Primitive mode unsupported: "+f.mode);Object.keys(m.geometry.morphAttributes).length>0&&uM(m,r),m.name=t.createUniqueName(r.name||"mesh_"+e),Ri(m,r),f.extensions&&Vs(i,m,f),t.assignFinalMaterial(m),u.push(m)}for(let p=0,g=u.length;p<g;p++)t.associations.set(u[p],{meshes:e,primitives:p});if(u.length===1)return r.extensions&&Vs(i,u[0],r),u[0];let d=new Ke;r.extensions&&Vs(i,d,r),t.associations.set(d,{meshes:e});for(let p=0,g=u.length;p<g;p++)d.add(u[p]);return d})}loadCamera(e){let t,n=this.json.cameras[e],i=n[n.type];if(!i){console.warn("THREE.GLTFLoader: Missing camera parameters.");return}return n.type==="perspective"?t=new zt(kt.radToDeg(i.yfov),i.aspectRatio||1,i.znear||1,i.zfar||2e6):n.type==="orthographic"&&(t=new Ti(-i.xmag,i.xmag,i.ymag,-i.ymag,i.znear,i.zfar)),n.name&&(t.name=this.createUniqueName(n.name)),Ri(t,n),Promise.resolve(t)}loadSkin(e){let t=this.json.skins[e],n=[];for(let i=0,r=t.joints.length;i<r;i++)n.push(this._loadNodeShallow(t.joints[i]));return t.inverseBindMatrices!==void 0?n.push(this.getDependency("accessor",t.inverseBindMatrices)):n.push(null),Promise.all(n).then(function(i){let r=i.pop(),a=i,o=[],c=[];for(let l=0,h=a.length;l<h;l++){let u=a[l];if(u){o.push(u);let d=new je;r!==null&&d.fromArray(r.array,l*16),c.push(d)}else console.warn('THREE.GLTFLoader: Joint "%s" could not be found.',t.joints[l])}return new pa(o,c)})}loadAnimation(e){let t=this.json,n=this,i=t.animations[e],r=i.name?i.name:"animation_"+e,a=[],o=[],c=[],l=[],h=[];for(let u=0,d=i.channels.length;u<d;u++){let p=i.channels[u],g=i.samplers[p.sampler],v=p.target,f=v.node,m=i.parameters!==void 0?i.parameters[g.input]:g.input,_=i.parameters!==void 0?i.parameters[g.output]:g.output;v.node!==void 0&&(a.push(this.getDependency("node",f)),o.push(this.getDependency("accessor",m)),c.push(this.getDependency("accessor",_)),l.push(g),h.push(v))}return Promise.all([Promise.all(a),Promise.all(o),Promise.all(c),Promise.all(l),Promise.all(h)]).then(function(u){let d=u[0],p=u[1],g=u[2],v=u[3],f=u[4],m=[];for(let b=0,x=d.length;b<x;b++){let T=d[b],S=p[b],A=g[b],y=v[b],E=f[b];if(T===void 0)continue;T.updateMatrix&&T.updateMatrix();let I=n._createAnimationTracks(T,S,A,y,E);if(I)for(let L=0;L<I.length;L++)m.push(I[L])}let _=new La(r,void 0,m);return Ri(_,i),_})}createNodeMesh(e){let t=this.json,n=this,i=t.nodes[e];return i.mesh===void 0?null:n.getDependency("mesh",i.mesh).then(function(r){let a=n._getNodeRef(n.meshCache,i.mesh,r);return i.weights!==void 0&&a.traverse(function(o){if(o.isMesh)for(let c=0,l=i.weights.length;c<l;c++)o.morphTargetInfluences[c]=i.weights[c]}),a})}loadNode(e){let t=this.json,n=this,i=t.nodes[e],r=n._loadNodeShallow(e),a=[],o=i.children||[];for(let l=0,h=o.length;l<h;l++)a.push(n.getDependency("node",o[l]));let c=i.skin===void 0?Promise.resolve(null):n.getDependency("skin",i.skin);return Promise.all([r,Promise.all(a),c]).then(function(l){let h=l[0],u=l[1],d=l[2];d!==null&&h.traverse(function(p){p.isSkinnedMesh&&p.bind(d,pM)});for(let p=0,g=u.length;p<g;p++)h.add(u[p]);if(h.userData.pivot!==void 0&&u.length>0){let p=h.userData.pivot,g=u[0];h.pivot=new R().fromArray(p),h.position.x-=p[0],h.position.y-=p[1],h.position.z-=p[2],g.position.set(0,0,0),delete h.userData.pivot}return h})}_loadNodeShallow(e){let t=this.json,n=this.extensions,i=this;if(this.nodeCache[e]!==void 0)return this.nodeCache[e];let r=t.nodes[e],a=r.name?i.createUniqueName(r.name):"",o=[],c=i._invokeOne(function(l){return l.createNodeMesh&&l.createNodeMesh(e)});return c&&o.push(c),r.camera!==void 0&&o.push(i.getDependency("camera",r.camera).then(function(l){return i._getNodeRef(i.cameraCache,r.camera,l)})),i._invokeAll(function(l){return l.createNodeAttachment&&l.createNodeAttachment(e)}).forEach(function(l){o.push(l)}),this.nodeCache[e]=Promise.all(o).then(function(l){let h;if(r.isBone===!0?h=new Mr:l.length>1?h=new Ke:l.length===1?h=l[0]:h=new ft,h!==l[0])for(let u=0,d=l.length;u<d;u++)h.add(l[u]);if(r.name&&(h.userData.name=r.name,h.name=a),Ri(h,r),r.extensions&&Vs(n,h,r),r.matrix!==void 0){let u=new je;u.fromArray(r.matrix),h.applyMatrix4(u)}else r.translation!==void 0&&h.position.fromArray(r.translation),r.rotation!==void 0&&h.quaternion.fromArray(r.rotation),r.scale!==void 0&&h.scale.fromArray(r.scale);if(!i.associations.has(h))i.associations.set(h,{});else if(r.mesh!==void 0&&i.meshCache.refs[r.mesh]>1){let u=i.associations.get(h);i.associations.set(h,{...u})}return i.associations.get(h).nodes=e,h}),this.nodeCache[e]}loadScene(e){let t=this.extensions,n=this.json.scenes[e],i=this,r=new Ke;n.name&&(r.name=i.createUniqueName(n.name)),Ri(r,n),n.extensions&&Vs(t,r,n);let a=n.nodes||[],o=[];for(let c=0,l=a.length;c<l;c++)o.push(i.getDependency("node",a[c]));return Promise.all(o).then(function(c){for(let h=0,u=c.length;h<u;h++){let d=c[h];d.parent!==null?r.add(rm(d)):r.add(d)}let l=h=>{let u=new Map;for(let[d,p]of i.associations)(d instanceof xn||d instanceof jt)&&u.set(d,p);return h.traverse(d=>{let p=i.associations.get(d);p!=null&&u.set(d,p)}),u};return i.associations=l(r),r})}_createAnimationTracks(e,t,n,i,r){let a=[],o=e.name?e.name:e.uuid,c=[];function l(p){p.morphTargetInfluences&&c.push(p.name?p.name:p.uuid)}gs[r.path]===gs.weights?(l(e),e.isGroup&&e.children.forEach(l)):c.push(o);let h;switch(gs[r.path]){case gs.weights:h=Gi;break;case gs.rotation:h=Vi;break;case gs.translation:case gs.scale:h=cs;break;default:switch(n.itemSize){case 1:h=Gi;break;case 2:case 3:default:h=cs;break}break}let u=i.interpolation!==void 0?lM[i.interpolation]:ws,d=this._getArrayFromAccessor(n);for(let p=0,g=c.length;p<g;p++){let v=new h(c[p]+"."+gs[r.path],t.array,d,u);i.interpolation==="CUBICSPLINE"&&this._createCubicSplineTrackInterpolant(v),a.push(v)}return a}_getArrayFromAccessor(e){let t=e.array;if(e.normalized){let n=td(t.constructor),i=new Float32Array(t.length);for(let r=0,a=t.length;r<a;r++)i[r]=t[r]*n;t=i}return t}_createCubicSplineTrackInterpolant(e){e.createInterpolant=function(n){let i=this instanceof Vi?Qu:Lc;return new i(this.times,this.values,this.getValueSize()/3,n)},e.createInterpolant.isInterpolantFactoryMethodGLTFCubicSpline=!0}};function mM(s,e,t){let n=e.attributes,i=new En;if(n.POSITION!==void 0){let o=t.json.accessors[n.POSITION],c=o.min,l=o.max;if(c!==void 0&&l!==void 0){if(i.set(new R(c[0],c[1],c[2]),new R(l[0],l[1],l[2])),o.normalized){let h=td(Vr[o.componentType]);i.min.multiplyScalar(h),i.max.multiplyScalar(h)}}else{console.warn("THREE.GLTFLoader: Missing min/max properties for accessor POSITION.");return}}else return;let r=e.targets;if(r!==void 0){let o=new R,c=new R;for(let l=0,h=r.length;l<h;l++){let u=r[l];if(u.POSITION!==void 0){let d=t.json.accessors[u.POSITION],p=d.min,g=d.max;if(p!==void 0&&g!==void 0){if(c.setX(Math.max(Math.abs(p[0]),Math.abs(g[0]))),c.setY(Math.max(Math.abs(p[1]),Math.abs(g[1]))),c.setZ(Math.max(Math.abs(p[2]),Math.abs(g[2]))),d.normalized){let v=td(Vr[d.componentType]);c.multiplyScalar(v)}o.max(c)}else console.warn("THREE.GLTFLoader: Missing min/max properties for accessor POSITION.")}}i.expandByVector(o)}s.boundingBox=i;let a=new yn;i.getCenter(a.center),a.radius=i.min.distanceTo(i.max)/2,s.boundingSphere=a}function hm(s,e,t){let n=e.attributes,i=[];function r(a,o){return t.getDependency("accessor",a).then(function(c){s.setAttribute(o,c)})}for(let a in n){let o=ed[a]||a.toLowerCase();o in s.attributes||i.push(r(n[a],o))}if(e.indices!==void 0&&!s.index){let a=t.getDependency("accessor",e.indices).then(function(o){s.setIndex(o)});i.push(a)}return it.workingColorSpace!==gn&&"COLOR_0"in n&&console.warn(`THREE.GLTFLoader: Converting vertex colors from "srgb-linear" to "${it.workingColorSpace}" not supported.`),Ri(s,e),mM(s,e,t),Promise.all(i).then(function(){return e.targets!==void 0?hM(s,e.targets,t):s})}var hi=Math.PI*2,Kn=6535167,ci=16170354,Qe=(s=>()=>(s=s*1664525+1013904223>>>0,s/4294967296))(71827),pt=(s=0,e=0,t=0)=>new R(s,e,t);function Hr(s,e){let t=document.createElement("canvas");t.width=t.height=s,e(t.getContext("2d"),s);let n=new Mi(t);return n.colorSpace=Ct,n}function gM(){return Hr(128,(s,e)=>{let t=s.createRadialGradient(e/2,e/2,0,e/2,e/2,e/2);t.addColorStop(0,"#fff"),t.addColorStop(.1,"#ffffffdd"),t.addColorStop(.4,"#ffffff44"),t.addColorStop(1,"#ffffff00"),s.fillStyle=t,s.fillRect(0,0,e,e)})}function xM(){return Hr(1024,(s,e)=>{s.translate(e/2,e/2),s.strokeStyle="#b1efd5",s.fillStyle="#b1efd5",s.lineWidth=2.5;for(let n of[476,458,389,370,237])s.beginPath(),s.arc(0,0,n,0,hi),s.stroke();for(let n=0;n<96;n++){let i=n*hi/96;s.save(),s.rotate(i),s.fillRect(-1,422,2,n%4?14:29),s.restore()}let t=["\u4E7E","\u5764","\u9707","\u5DFD","\u574E","\u79BB","\u826E","\u5151"];s.font="38px serif",s.textAlign="center",s.textBaseline="middle";for(let n=0;n<8;n++){s.save(),s.rotate(n*Math.PI/4),s.fillText(t[n],0,-327);for(let i=0;i<3;i++)n>>i&1?(s.fillRect(-35,-290+i*12,26,5),s.fillRect(9,-290+i*12,26,5)):s.fillRect(-35,-290+i*12,70,5);s.restore()}for(let n=0;n<2;n++)s.save(),s.rotate(n*Math.PI/4),s.strokeRect(-164,-164,328,328),s.restore();s.lineWidth=4,s.beginPath(),s.moveTo(0,-185),s.lineTo(75,-75),s.lineTo(0,0),s.lineTo(-75,75),s.lineTo(0,185),s.stroke(),s.beginPath(),s.arc(0,0,190,0,hi),s.stroke()})}var Nc=class{constructor(e,t=()=>{}){this.container=e,this.onProgress=t,this.scene=new ss,this.scene.background=new Me(5400180),this.scene.fog=new ua(4281693,38,140),this.camera=new zt(58,innerWidth/innerHeight,.06,600),this.camera.position.set(1.5,2.6,16),this.renderer=new pc({antialias:!0,powerPreference:"high-performance"}),this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.6)),this.renderer.setSize(innerWidth,innerHeight),this.renderer.shadowMap.enabled=!0,this.renderer.shadowMap.type=Ds,this.renderer.toneMapping=Fs,this.renderer.toneMappingExposure=1.12,this.renderer.outputColorSpace=Ct,e.appendChild(this.renderer.domElement),this.renderer.domElement.setAttribute("aria-label","\u5B9E\u65F6\u4E09\u7EF4\u5C71\u95E8\u573A\u666F"),this.composer=new Ec(this.renderer),this.composer.addPass(new Cc(this.scene,this.camera)),this.bloom=new Gr(new ne(innerWidth,innerHeight),.48,.6,1.05),this.composer.addPass(this.bloom),this.composer.addPass(new Rc),this.loader=new Ls,this.geo={box:new Mn(1,1,1),sphere:new Nt(1,24,16),rock:new Vt(1,1)},this.thunderPaper=Hr(512,(i,r)=>{i.fillStyle="#d8aa58",i.fillRect(0,0,r,r),i.strokeStyle="#713321",i.lineWidth=10,i.strokeRect(24,16,464,480),i.fillStyle="#57243a",i.font="bold 86px serif",i.textAlign="center",[..."\u4E94\u96F7\u6555\u4EE4"].forEach((a,o)=>i.fillText(a,256,110+o*108))}),this.guardPaper=Hr(512,(i,r)=>{i.fillStyle="#e7b35d",i.fillRect(0,0,r,r),i.strokeStyle="#a2491d",i.lineWidth=8,i.strokeRect(22,16,468,480),i.fillStyle="#8c3618",i.font="bold 84px serif",i.textAlign="center",[..."\u62A4\u8EAB\u6555\u4EE4"].forEach((a,o)=>i.fillText(a,256,110+o*108))}),this.glow=gM(),this.runes=xM(),this.emitters=[],this.ribbons=[],this.lanterns=[],this.particles=[],this.projectiles=[],this.ripples=[],this.spellEffects=[],this.move=pt(),this.position=pt(0,1.75,13),this.yaw=0,this.pitch=0,this.dragging=!1,this.shake=0,this.recoil=0,this.handMode="idle",this.handUntil=0,this.bandPose="",this.bandTilt={pitch:0,roll:0},this.time=0,this.startBlend=0,this.failedAssets=[],this.viewScene=new ss,this.viewCamera=new zt(53,innerWidth/innerHeight,.01,8),this.viewScene.add(this.viewCamera),this.handFill=new hs(10009343,3153945,1.1),this.viewScene.add(this.handFill),this.handKey=new Nn(16759939,2.2),this.handKey.position.set(-2,3,2),this.viewScene.add(this.handKey);let n=new Nn(7650559,.9);n.position.set(2,1,-3),this.viewScene.add(n),this.handRig=new Ke,this.handRig.scale.setScalar(.82),this.viewCamera.add(this.handRig),this.handRig.position.set(.29,-.35,-.67),this.handLight=new Ln(Kn,0,2),this.handLight.position.set(.1,.15,-.1),this.handRig.add(this.handLight),window.addEventListener("resize",()=>this.resize())}async texture(e,t=1){try{let n=await this.loader.loadAsync("./assets/"+e);return n.wrapS=n.wrapT=_i,n.repeat.set(t,t),n.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy()),(e.includes("color")||e.includes("sky"))&&(n.colorSpace=Ct),n}catch{return this.failedAssets.push(e),null}}async init(){this.onProgress("\u6B63\u5728\u94FA\u8BBE\u77F3\u5EAD\u4E0E\u8FDC\u5C71\u2026");let[e,t,n,i,r,a,o]=await Promise.all([this.texture("floor-color.jpg",12),this.texture("floor-normal.jpg",12),this.texture("floor-rough.jpg",12),this.texture("rock-color.jpg",2),this.texture("rock-normal.jpg",2),this.texture("rock-rough.jpg",2),this.texture("sky-mountains.png")]);if(this.materials={stone:new nt({color:9082513,map:i,normalMap:r,roughnessMap:a,roughness:.85,normalScale:new ne(.6,.6)}),floor:new It({color:10268330,map:e,normalMap:t,roughnessMap:n,roughness:.55,metalness:.08,clearcoat:.8,clearcoatRoughness:.22,normalScale:new ne(.8,.8)}),darkStone:new nt({color:3623236,map:i,normalMap:r,roughness:.8}),wood:new nt({color:5450787,roughness:.7}),woodLight:new nt({color:8802362,roughness:.7}),metal:new nt({color:10322001,metalness:.7,roughness:.4}),roof:new nt({color:3033935,roughness:.66,metalness:.15}),light:new nt({color:16763276,emissive:16754765,emissiveIntensity:2.3,roughness:.5}),cloth:new nt({color:1387825,roughness:.8,side:st}),energy:new Ye({color:Kn,toneMapped:!1}),fire:new Ye({color:ci,toneMapped:!1})},o){let c=new Ee(new Nt(290,48,32),new Ye({map:o,fog:!1,toneMapped:!1,side:qt}));c.position.y=25,this.scene.add(c),this.skyMaterial=c.material,this.skyDome=c,c.material.transparent=!0,c.material.depthWrite=!1,c.renderOrder=-1e3;let l=o.clone();l.mapping=Pr,l.needsUpdate=!0,this.scene.environment=l,this.scene.environmentIntensity=.35}this.lighting(),this.courtyard(),this.temple(0,-27,1.15,!0),this.temple(-26,-30,.58),this.temple(27,-35,.62),this.gate(),this.landscape(),this.buildGateDoors(),this.buildEnemy(),this.actors=new Tc(this),em(this),$p(this),Zp(this),this.buildAmbient(),this.onProgress("\u6B63\u5728\u5524\u9192\u5251\u8BC0\u4E0E\u62A4\u8EAB\u5370\u2026"),await this.buildHand(),await Up(this),this.ending=new _c(this),await this.ending.init(),this.onProgress("\u5C71\u95E8\u5DF2\u5F00"),this.resize()}mesh(e,t,n=0,i=0,r=0,a=1,o=a,c=a,l=this.scene){let h=new Ee(e,t);return h.position.set(n,i,r),h.scale.set(a,o,c),h.castShadow=!0,h.receiveShadow=!0,l.add(h),h}box(e,t,n,i,r,a,o,c){return this.mesh(this.geo.box,e,t,n,i,r,a,o,c)}cylinder(e,t,n,i,r,a,o,c=this.scene,l=12){return this.mesh(new _n(t,n,i,l),e,r,a,o,1,1,1,c)}tube(e,t,n,i=this.scene){let r=new Pn(e.map(a=>Array.isArray(a)?pt(...a):a));return this.mesh(new Wn(r,Math.max(12,e.length*6),t,6,!1),n,0,0,0,1,1,1,i)}lighting(){this.hemi=new hs(11916519,2108480,2.1),this.scene.add(this.hemi);let e=this.sun=new Nn(16767138,3.5);e.position.set(22,35,-16),e.castShadow=!0,e.shadow.mapSize.set(2048,2048),Object.assign(e.shadow.camera,{left:-30,right:30,top:32,bottom:-28,near:1,far:100}),e.shadow.normalBias=.05,e.shadow.bias=-2e-4,this.scene.add(e),e.target.position.set(0,0,-10),this.scene.add(e.target);let t=this.fill=new Nn(9157073,1);t.position.set(-20,12,15),this.scene.add(t),this.enemyLight=new Ln(15114338,22,18,2),this.enemyLight.position.set(0,4,-8),this.scene.add(this.enemyLight)}courtyard(){let e=this.materials;this.box(e.stone,0,-1.25,-4,36,2.4,55),this.box(e.darkStone,0,-.17,-4,36.7,.22,55.7);let t=this.mesh(new Rt(35.8,55,1,1),e.floor,0,-.04,-4);t.rotation.x=-Math.PI/2;let n=new nt({color:7108714,metalness:.25,roughness:.6});for(let a of[-17,17]){this.box(e.stone,a,.12,-4,.9,.3,54);for(let o=-29;o<=21;o+=3.4)this.box(e.stone,a,1,o,.42,1.8,.42),this.box(n,a,1.95,o,.68,.18,.68),this.mesh(new Nt(.24,8,6),e.stone,a,2.15,o);for(let o of[.5,1.4])this.box(e.stone,a,o,-4,.19,.17,52)}for(let a=-24;a<18;a+=4)for(let o of[-13.3,13.3])this.box(e.darkStone,o,.01,a,2,.12,2.5),this.box(e.stone,o,.08,a,1.65,.12,2.15);for(let a=0;a<8;a++)this.box(e.stone,0,a*.2,-18-a*.7,14-a*.25,.28,.8);let i=new Ye({map:this.runes,transparent:!0,opacity:.55,depthWrite:!1,blending:dt,color:9618857,toneMapped:!1});this.groundSeal=new Ee(new Rt(14,14),i),this.groundSeal.rotation.x=-Math.PI/2,this.groundSeal.position.set(0,.012,-6),this.scene.add(this.groundSeal);let r=new It({color:6981520,roughness:.04,metalness:.45,transparent:!0,opacity:.24,clearcoat:1,depthWrite:!1});for(let a=0;a<20;a++){let o=this.mesh(new _a(1,24),r,(Qe()-.5)*27,.008,(Qe()-.5)*36-3,1+Qe()*2,1,1);o.rotation.x=-Math.PI/2,o.scale.y=.3+Qe()*.6,o.castShadow=!1}for(let a of[-10.7,10.7])for(let o of[-17,-7,5,16])this.lantern(a,o);for(let a=0;a<35;a++){let o=(Qe()<.5?-1:1)*(12+Qe()*4),c=Qe()*48-28;this.mesh(this.geo.rock,e.darkStone,o,.02,c,.2+Qe()*.5,.1+Qe()*.3,.3+Qe()*.4).rotation.y=Qe()*hi}}roof(e,t,n,i,r){let c=[],l=[],h=[],u=(_,b)=>r*(1-Math.abs(b))*.9-r*.4*Math.max(0,(Math.abs(_)-.62)/.38)+Math.pow(Math.abs(_),6)*.55+Math.pow(Math.abs(b),8)*.45;for(let _=0;_<=18;_++)for(let b=0;b<=40;b++){let x=b/40*2-1,T=_/18*2-1;c.push(x*n/2,u(x,T)+t,T*i/2),l.push(b/40*8,_/18*4)}for(let _=0;_<18;_++)for(let b=0;b<40;b++){let x=_*41+b;h.push(x,x+1,x+40+1,x+1,x+40+2,x+40+1)}let d=new tt;d.setAttribute("position",new Oe(c,3)),d.setAttribute("uv",new Oe(l,2)),d.setIndex(h),d.computeVertexNormals();let p=this.mesh(d,this.materials.roof,0,0,0,1,1,1,e);p.material.side=st;for(let _ of[-1,1])this.tube(Array.from({length:17},(b,x)=>{let T=x/8-1;return[T*n/2,t+u(T,_),_*i/2]}),.065,this.materials.metal,e);this.tube([[-n*.48,t+r*.75,0],[-n*.28,t+r*.94,0],[0,t+r*.9,0],[n*.28,t+r*.94,0],[n*.48,t+r*.75,0]],.12,this.materials.roof,e);let g=new _n(.075,.075,i/2*.95,5,1,!0),v=new un(g,this.materials.roof,Math.floor(n/.22)*2),f=new ft,m=0;for(let _=-n/2+.12;_<n/2-.1;_+=.22)for(let b of[-1,1]){let x=_/(n/2);f.position.set(_,t+u(x,.5),b*i*.25),f.rotation.set(b*(Math.PI/2+Math.atan(r*.9/(i/2))),0,0),f.updateMatrix(),m<v.count&&v.setMatrixAt(m++,f.matrix)}v.count=m,v.castShadow=!0,e.add(v)}temple(e,t,n,i=!1){let r=new Ke;r.position.set(e,1.5,t),r.rotation.y=Math.PI,r.scale.setScalar(n),this.scene.add(r);let a=this.materials;if(this.box(a.stone,0,i?-.25:0,0,18,i?.5:.8,10,r),i){for(let c of[-1,1])this.box(a.wood,c*4.85,3,1,5.3,5.5,7,r);this.box(a.wood,0,5.35,1,4.4,.8,7,r)}else this.box(a.wood,0,3,1,15,5.5,7,r);for(let c of i?[-7,-3.5,3.5,7]:[-7,-3.5,0,3.5,7]){this.cylinder(a.woodLight,.2,.26,5.8,c,3.1,-3.6,r),this.cylinder(a.metal,.3,.32,.2,c,.55,-3.6,r),this.cylinder(a.metal,.25,.25,.12,c,5.4,-3.6,r);for(let l=0;l<3;l++)this.box(a.woodLight,c,5.4+l*.17,-3.6,.9+l*.4,.13,.4,r)}for(let c of i?[-5.3,5.3]:[-5.3,-1.8,1.8,5.3]){this.box(new nt({color:9136454,emissive:16757611,emissiveIntensity:.18,roughness:.9}),c,3,-2.55,2.6,3.7,.05,r);for(let l=-1;l<=1;l+=.33)this.box(a.wood,c+l,3,-2.6,.055,3.8,.12,r);for(let l=1.2;l<5;l+=.42)this.box(a.wood,c,l,-2.65,2.7,.06,.12,r)}this.roof(r,6,20,12,2.6),this.box(a.wood,0,8,0,10,2.4,5.5,r),this.roof(r,9.4,14,8.2,1.9);for(let c of[-4.7,0,4.7])this.cylinder(a.woodLight,.15,.15,2.2,c,8.1,-2.9,r);let o=Hr(512,(c,l)=>{c.fillStyle="#18302d",c.fillRect(0,0,l,l),c.strokeStyle="#ae8651",c.lineWidth=9,c.strokeRect(20,150,l-40,210),c.font="85px serif",c.textAlign="center",c.fillStyle="#d1b478",c.fillText("\u592A \u7384 \u89C2",l/2,290)});this.box(new nt({map:o,roughness:.65}),0,5,-3.8,4.6,1.3,.14,r)}gate(){let e=new Ke;e.position.set(0,0,20.8),this.scene.add(e);let t=this.materials;for(let n of[-12,12])this.box(t.stone,n,1.5,0,1.8,3,1.8,e),this.cylinder(t.wood,.43,.55,8,n,6.6,0,e),this.cylinder(t.metal,.58,.58,.2,n,3.1,0,e);this.box(t.wood,0,10.1,0,27,.7,.9,e),this.roof(e,10.5,29,4.4,1.9)}lantern(e,t){let n=this.materials;this.box(n.stone,e,.3,t,.95,.6,.95),this.cylinder(n.darkStone,.15,.22,1.7,e,1.35,t),this.box(n.metal,e,2.3,t,.7,.12,.7);let i=this.mesh(new _n(.34,.28,.7,8),n.light,e,2.7,t);this.lanterns.push(i);for(let a=0;a<8;a++){let o=a*hi/8;this.box(n.wood,e+Math.cos(o)*.32,2.7,t+Math.sin(o)*.32,.045,.75,.045)}this.cylinder(n.roof,.04,.52,.3,e,3.2,t),this.cylinder(n.metal,.08,.08,.13,e,3.42,t);let r=new Cn(new vn({map:this.glow,color:16753483,transparent:!0,opacity:.26,blending:dt,depthWrite:!1}));if(r.position.set(e,2.7,t),r.scale.set(2.8,2.8,1),this.scene.add(r),t===-7||t===5){let a=new Ln(16756034,65,15,2);a.position.set(e,2.8,t),this.scene.add(a)}}tree(e,t,n=1){let i=new Ke;i.position.set(e,-1,t),i.scale.setScalar(n),this.scene.add(i);let r=new nt({color:3423276,map:this.materials.stone.map,roughness:1});this.tube([[0,0,0],[.2,2,0],[-.3,4,.3],[.7,6,0],[.3,8,0]],.24,r,i);let a=new nt({color:11501365,roughness:.95,side:st}),o=new Nt(1,5,3),c=new un(o,a,2600),l=new ft;for(let h=0;h<5;h++){let u=h*2.4;this.tube([[0,3+h*.7,0],[Math.cos(u)*1.8,4+h*.7,Math.sin(u)*1.8],[Math.cos(u)*3,4.8+h*.7,Math.sin(u)*2.6]],.12,r,i)}for(let h=0;h<2600;h++){let u=Qe()*hi,d=Math.sqrt(Qe())*3.4;l.position.set(Math.cos(u)*d,5+Qe()*3,Math.sin(u)*d*.8),l.scale.set(.06+Qe()*.12,.012+Qe()*.015,.08+Qe()*.14),l.rotation.set(Qe(),Qe()*hi,Qe()),l.updateMatrix(),c.setMatrixAt(h,l.matrix),c.setColorAt(h,new Me().setHSL(.09+Qe()*.06,.42,.25+Qe()*.18))}c.castShadow=!0,i.add(c)}landscape(){let e=this.materials;for(let r=0;r<35;r++){let a=r%2?1:-1,o=a*(23+Qe()*70),c=-25-Qe()*100,l=8+Qe()*28,h=c<-35&&Math.abs(o-qn(c))<18?qn(c)+a*24:o,u=this.mesh(new Vt(1,2),e.stone,h,-10,c,4+Qe()*10,l,4+Qe()*9);u.rotation.y=Qe()*hi}for(let r of[[-20,6,1.2],[22,-3,1.45],[-24,-18,1.6],[25,14,1.15],[-29,-36,2]])this.tree(...r);let t=new nt({color:6647881,side:st,roughness:1}),n=new un(new Rt(.08,.65),t,500),i=new ft;for(let r=0;r<500;r++)i.position.set((r%2?1:-1)*(15+Qe()*1.5),.25,Qe()*50-29),i.rotation.set(.1,Qe()*hi,Qe()*.5-.25),i.scale.setScalar(.3+Qe()),i.updateMatrix(),n.setMatrixAt(r,i.matrix);this.scene.add(n)}buildGateDoors(){this.gateDoors=[],this.gateOpenAt=1/0;for(let e of[-1,1]){let t=new Ke;t.position.set(e*2.4,1.35,-22.1),this.scene.add(t);let n=-e*1.2;this.box(this.materials.wood,n,2.25,0,2.4,4.5,.24,t),this.box(this.materials.metal,n,4.25,.14,2.35,.06,.04,t),this.box(this.materials.metal,n,.28,.14,2.35,.06,.04,t);for(let i=.65;i<4;i+=.6)for(let r=-.8;r<=.8;r+=.55)this.mesh(new Nt(.045,6,5),this.materials.metal,n+r,i,.16,1,1,1,t);this.gateDoors.push({g:t,sign:e})}}buildEnemy(){let e=new Ke;e.position.set(0,2.8,-9),this.enemy=e,this.scene.add(e);let t=this.materials,n=new nt({color:1581606,metalness:.38,roughness:.48}),i=new nt({color:2369843,metalness:.7,roughness:.32,map:t.stone.map});this.enemyMaterials=[n,i];let r=new _n(.48,1.05,2.45,32,12,!0),a=r.attributes.position;for(let l=0;l<a.count;l++){let h=a.getX(l),u=a.getZ(l),d=a.getY(l),p=Math.atan2(u,h),g=1+Math.sin(p*11)*.085;a.setXYZ(l,h*g,d+(d<-.9?Math.sin(p*5)*.2:0),u*g)}r.computeVertexNormals(),this.mesh(r,t.cloth,0,-.5,0,1,1,1,e),this.mesh(new Nt(1,24,16),n,0,.9,0,.62,.72,.38,e),this.mesh(new Vt(1,1),i,0,1.74,.06,.4,.59,.29,e);let o=new Ke;o.position.set(0,1.8,.3),e.add(o);for(let l of[-1,1]){this.tube([[l*.15,.42,0],[l*.43,.68,-.03],[l*.5,1.03,-.15],[l*.38,1.37,-.2]],.065,i,o);let h=this.box(t.fire,l*.19,.08,.1,.2,.045,.04,o);h.rotation.z=l*.2,this.tube([[l*.07,.18,.07],[l*.22,.29,.02],[l*.37,.14,-.01],[l*.28,-.1,.04],[l*.13,-.36,.01]],.024,t.metal,o);for(let d=0;d<3;d++){let p=this.mesh(new Vt(1,0),i,l*(.7+d*.14),1.07-d*.13,.03,.4-d*.045,.22,.43-d*.05,e);p.rotation.z=l*(-.22-d*.14)}let u=this.tube([[l*.7,.75,0],[l*1.12,.25,.03],[l*1.4,-.1,.22]],.14,n,e);this.ribbons.push({obj:u,base:u.rotation.z,sign:l}),this.mesh(new Nt(.17,12,8),i,l*1.4,-.12,.24,1,1,1,e),this.tube([[l*.53,.52,.23],[l*.78,-.2,.38],[l*.62,-1.25,.32],[l*1.1,-1.9,.1]],.055,t.metal,e)}this.tube([[0,2.3,.32],[0,1.9,.35],[-.06,1.72,.36],[.06,1.72,.36],[0,1.56,.32]],.022,t.metal,e);for(let l of[-1,1])for(let h=0;h<4;h++){let u=this.mesh(new Vt(1,0),i,l*(.33+h*.1),.65-h*.54,.27,.35,.44,.18,e);u.rotation.z=l*(.13+h*.08)}for(let l of[.72,-.02]){let h=new Ee(new si(l>0?.23:.14,.025,8,32),t.fire);h.position.set(0,l,.46),e.add(h)}this.core=this.mesh(new Hn(.18),t.fire,0,.65,.42,1,1.4,1,e),this.halo=new Ee(new Rt(5,5),new Ye({map:this.runes,transparent:!0,opacity:.33,blending:dt,color:16104828,depthWrite:!1,side:st,toneMapped:!1})),this.halo.position.set(0,.6,-.5),e.add(this.halo);let c=Hr(256,(l,h)=>{l.fillStyle="#b79a5a",l.fillRect(0,0,h,h),l.strokeStyle="#593f27",l.lineWidth=8,l.strokeRect(15,12,h-30,h-24),l.font="55px serif",l.textAlign="center",l.fillStyle="#38291e";for(let[u,d]of[..."\u9547\u5C71\u6555\u4EE4"].entries())l.fillText(d,128,65+u*54)});this.talismans=[];for(let l=0;l<8;l++){let h=new Ee(new Rt(.3,.75),new nt({map:c,side:st,color:14664080,emissive:2891528,roughness:.8}));e.add(h),this.talismans.push(h)}this.aura=new Cn(new vn({map:this.glow,color:15706723,transparent:!0,opacity:.13,blending:dt,depthWrite:!1})),this.aura.scale.set(7,7,1),this.aura.position.y=.5,e.add(this.aura)}buildAmbient(){let t=new tt,n=new Float32Array(720),i=new Float32Array(720);this.ambientBase=[];for(let a=0;a<240;a++){let o=[(Qe()-.5)*35,Qe()*14,Qe()*45-25];n.set(o,a*3),this.ambientBase.push(o);let c=new Me(a%3?14072698:9756103);i.set([c.r,c.g,c.b],a*3)}t.setAttribute("position",new Ft(n,3)),t.setAttribute("color",new Ft(i,3)),this.ambient=new Gn(t,new Rn({map:this.glow,size:.1,transparent:!0,opacity:.45,vertexColors:!0,blending:dt,depthWrite:!1})),this.scene.add(this.ambient);let r=new tt;this.fxPositions=new Float32Array(1500*3),this.fxColors=new Float32Array(1500*3),r.setAttribute("position",new Ft(this.fxPositions,3)),r.setAttribute("color",new Ft(this.fxColors,3)),r.setDrawRange(0,0),this.fxPoints=new Gn(r,new Rn({map:this.glow,size:.12,transparent:!0,vertexColors:!0,blending:dt,depthWrite:!1,toneMapped:!1})),this.scene.add(this.fxPoints)}async buildHand(){this.bones=[];try{let r=await new Ic().loadAsync("./assets/hand-right.glb");this.handModel=r.scene;let a=new Ke;this.handRig.add(a),a.quaternion.setFromAxisAngle(pt(0,0,1),Math.PI).multiply(new nn().setFromAxisAngle(pt(0,1,0),-Math.PI/2)),a.scale.setScalar(1.85);let o=r.scene.getObjectByName("wrist");r.scene.position.copy(o.position).multiplyScalar(-1),a.add(r.scene);let c=tm();r.scene.traverse(l=>{l.isMesh&&(l.geometry=nm(l.geometry),l.material=c,l.frustumCulled=!1,l.castShadow=!1),l.isBone&&this.bones.push({node:l,p:l.position.clone(),q:l.quaternion.clone()})}),this.fingerNames=["index","middle","ring","pinky"],im(this)}catch{throw this.failedAssets.push("hand-right.glb"),new Error("\u624B\u90E8\u6A21\u578B\u672A\u52A0\u8F7D\uFF0C\u8BF7\u68C0\u67E5\u8FDE\u63A5\u540E\u91CD\u65B0\u8F7D\u5165\u3002")}let e=new It({color:725019,roughness:.92,sheen:.5,sheenColor:5660792}),t=new It({color:527377,metalness:0,roughness:.48,clearcoat:.12}),n=new _n(.073,.137,.52,48,20,!0),i=n.attributes.position;for(let r=0;r<i.count;r++){let a=i.getY(r),o=Math.atan2(i.getZ(r),i.getX(r)),c=1+.035*Math.sin(a*73+o*3)+.025*Math.cos(o*9+a*27);i.setX(r,i.getX(r)*c),i.setZ(r,i.getZ(r)*c*(.7+.3*(.26-a)/.52))}n.computeVertexNormals(),this.mesh(n,e,0,-.3,0,1,1,1,this.handRig),this.bandShell=this.mesh(new _n(.076,.079,.052,48,1,!0),t,0,-.025,0,1,1,.7,this.handRig),this.bandPieces=[],this.braceletMaterial=new nt({color:7596799,emissive:53247,emissiveIntensity:4,roughness:.4,metalness:0,toneMapped:!1});for(let r=0;r<8;r++){let a=r*hi/8,o=this.box(this.braceletMaterial,Math.cos(a)*.077,-.025,Math.sin(a)*.054,.019,.019,.004,this.handRig);o.rotation.y=-a+Math.PI/2,this.bandPieces.push({mesh:o,p:o.position.clone(),q:o.quaternion.clone(),angle:a})}this.handSigil=new Ee(new Rt(.34,.34),new Ye({map:this.runes,color:Kn,transparent:!0,opacity:0,blending:dt,depthWrite:!1,side:st,toneMapped:!1})),this.handSigil.position.set(-.05,.24,-.02),this.handRig.add(this.handSigil),this.guardRing=new Ee(new Rt(1.5,1.5),new Ye({map:this.runes,color:Kn,transparent:!0,opacity:0,blending:dt,depthWrite:!1,side:st,toneMapped:!1})),this.guardRing.position.set(0,-.02,-1),this.viewCamera.add(this.guardRing),Gp(this)}pose(e,t){let n=fi[e],i=n?.curls||[.08,.14,.22,.31];this.currentCurls||=[0,0,0,0],this.currentSpread||=[0,0,0,0];let r=(h,u,d=0)=>{let p=h.map(v=>this.bones.find(f=>f.node.name===v));if(p.some(v=>!v))return;let g=new nn().setFromAxisAngle(pt(1,0,0),d);for(let v=0;v<p.length;v++){let f=p[v],m=-u*[1.05,1.8,2.2,2.2][v],_=g.clone().multiply(new nn().setFromAxisAngle(pt(0,0,1),m));if(v===0)f.node.position.copy(f.p);else{let b=p[v-1],x=g.clone().multiply(new nn().setFromAxisAngle(pt(0,0,1),-u*[1.05,1.8,2.2][v-1]));f.node.position.copy(b.node.position).add(f.p.clone().sub(b.p).applyQuaternion(x))}f.node.quaternion.copy(_).multiply(f.q)}};for(let h=0;h<4;h++){this.currentCurls[h]=kt.damp(this.currentCurls[h],i[h],16,t),this.currentSpread[h]=kt.damp(this.currentSpread[h],n?.spread[h]||0,16,t);let u=this.fingerNames[h];r(["proximal","intermediate","distal"].map(d=>`${u}-finger-phalanx-${d}`).concat(`${u}-finger-tip`),this.currentCurls[h],this.currentSpread[h])}this.thumbCurl=kt.damp(this.thumbCurl||0,n?.thumb||0,14,t);let o=["thumb-metacarpal","thumb-phalanx-proximal","thumb-phalanx-distal","thumb-tip"].map(h=>this.bones.find(u=>u.node.name===h)),c=[o[0].p,pt(.006,.002,-.015),pt(.002,-.022,.004),pt(.006,-.025,.018)],l=Math.min(1,this.thumbCurl);o.forEach((h,u)=>h.node.position.copy(h.p).lerp(c[u],l)),o.forEach((h,u)=>{if(u<3){let d=o[u+1].p.clone().sub(h.p).normalize(),p=o[u+1].node.position.clone().sub(h.node.position).normalize();h.node.quaternion.setFromUnitVectors(d,p).multiply(h.q)}else h.node.quaternion.copy(o[u-1].node.quaternion)})}emitParticles(e,t,n=55,i=5){let r=new Me(t);for(let a=0;a<n;a++){let o=pt(Qe()-.5,Qe()-.25,Qe()-.5).normalize().multiplyScalar(i*(.2+Qe()));this.particles.push({p:e.clone(),v:o,color:r.clone(),life:.4+Qe()*.9,max:1.3})}this.particles.length>1500&&this.particles.splice(0,this.particles.length-1500)}shot(e,t,n,i=.3,r="orb"){let a=r==="sword"?Op():new Ee(new Nt(.07,12,8),new Ye({color:n,toneMapped:!1}));a.position.copy(e),r==="sword"&&(a.scale.setScalar(.7),a.quaternion.setFromUnitVectors(pt(0,1,0),t.clone().sub(e).normalize())),this.scene.add(a);let o=new ii(new tt().setFromPoints([e,e]),new zn({color:n,transparent:!0,opacity:.85,toneMapped:!1}));this.scene.add(o),this.projectiles.push({from:e.clone(),to:t.clone(),mesh:a,trail:o,age:0,life:i,color:n})}ring(e,t,n=5){let i=new Ee(new Rt(n,n),new Ye({map:this.runes,color:t,transparent:!0,opacity:.8,blending:dt,side:st,depthWrite:!1,toneMapped:!1}));i.position.copy(e),this.scene.add(i),this.ripples.push({mesh:i,age:0})}clearHazard(){this.hazardCircle&&(this.hazardCircle.removeFromParent(),this.hazardCircle.geometry.dispose(),this.hazardCircle.material.dispose(),this.hazardCircle=null)}effect(e){let t=this.actors?.position(e.enemyId)||this.enemy.position.clone().add(pt(0,.65,.3));if(["sword","guard","thunder"].includes(e.type)&&(this.handMode=e.type,this.handUntil=this.time+{sword:.8,guard:1.1,thunder:1.2}[e.type],this.handLight.intensity=e.type==="guard"?3:2,Vp(this,e.type)),e.type==="sword"){this.recoil=.07;let n=this.camera.position.clone().add(pt(.3,-.1,-.7).applyQuaternion(this.camera.quaternion));kp(this,n,t);for(let i=0;i<3;i++)this.shot(n.clone().add(pt((i-1)*.12,0,0)),t,Kn,.48+i*.06,"sword")}if(e.type==="thunder"&&(this.recoil=.1,this.shake=.055,bu(this,t),this.handLight.color.set(16756021)),e.type==="guard"&&(this.guardRing.material.color.set(15125384),this.handLight.color.set(15125384)),e.type==="sword"&&this.handLight.color.set(Kn),e.type==="spawn"&&(this.ring(t,11199182,4),this.emitParticles(t,9097914,55,5)),e.type==="enemy-dodge"&&this.emitParticles(t,9549813,65,6),e.type==="enemy-killed"&&(Hp(this,t,this.actors?.map.get(e.enemyId)?.kind),this.shake=.11),e.type==="area"){this.currentArea=e.area,this.scene.fog.color.set([4281693,6648705,4613994,2564913][e.area]);let n=$t[e.area].camera;this.position.set(e.area===1?qn(n.z):n.x,(n.y??1.75)+(e.area===1?Ki(n.z):0),n.z),this.skyMaterial&&this.skyMaterial.color.set(e.area===3?8222618:e.area===2?11719896:16777215),this.yaw=0,this.pitch=0}if(e.type==="travel"){if(this.travelArea=e.area,this.travelDuration=e.duration,this.travelStart=this.time,this.travelFrom=this.camera.position.clone(),this.travelTo=pt($t[e.area].camera.x,$t[e.area].camera.y??1.75,$t[e.area].camera.z),this.yaw=0,this.pitch=0,e.area===1)this.gateOpenAt=this.time,this.emitParticles(pt(0,3,-22),ci,80,3);else{let n=this.camera.position.clone().add(pt(0,2,-10));this.emitParticles(n,ci,350,15),this.ring(n,ci,15)}this.shake=.06}if(e.type==="expose"&&this.ring(this.camera.position.clone().add(pt(0,0,-2)),11204561,6),e.type==="armor-break"&&(this.emitParticles(t,ci,160,10),this.ring(t,ci,5)),e.type==="hazard-warning"&&(this.clearHazard(),this.hazardCircle=new Ee(new ki(.05,e.position.radius,48),new Ye({color:11562751,transparent:!0,opacity:.25,side:st,depthWrite:!1})),this.hazardCircle.rotation.x=-Math.PI/2,this.hazardCircle.position.set(e.position.x,.08,e.position.z),this.scene.add(this.hazardCircle)),e.type==="hazard-strike"){let n=pt(e.position.x,.2,e.position.z);vc(this,n.clone().add(pt(0,12,0)),n),this.emitParticles(n,11904255,110,8),this.clearHazard()}if(e.type==="finish"&&(this.outcome="victory",this.outcomeAt=this.time,this.ending.start()),e.type==="defeat"&&(this.outcome="defeat",this.outcomeAt=this.time),e.type==="enemy-hit"&&(this.actors?.hit(e.enemyId),this.emitParticles(t,ci,30,3),this.enemyHit=1),e.type==="enemy-cast"){let n=this.camera.position.clone();for(let i=0;i<3;i++)this.shot(t.clone().add(pt((i-1)*.5,.2,0)),n,ci,.8)}if(e.type==="parry"&&(this.shake=.07,this.ring(t,Kn,5),this.shot(this.camera.position,t,Kn,.2),this.emitParticles(t,Kn,120,6)),e.type==="block"&&(this.shake=.03,this.emitParticles(this.camera.position.clone().add(pt(0,0,-1)),Kn,20,2)),e.type==="hit"&&(this.shake=.17),e.type==="dash"){let n=this.currentArea===1?xt.safeX:this.currentArea===2?3.5:11.5,i=this.currentArea===1?qn(this.position.z):this.currentArea===2?yt.x:0;this.position.x=kt.clamp(this.position.x+(this.move.x<0?-2.6:2.6),i-n,i+n),this.recoil=.04}if(e.type==="stage"&&(this.ring(t,ci,8),this.emitParticles(t,ci,100,7)),e.type==="finish"&&(bu(this,t),this.emitParticles(t,Kn,450,12),this.ring(t,Kn,12),this.enemy.visible=!1,this.shake=.08),e.type==="reset"){this.ending?.reset(),Xp(this),this.outcome=null,this.clearHazard(),this.gateOpenAt=1/0,this.actors?.reset();for(let n of this.spellEffects)this.scene.remove(n.root),Yi(n.root);this.spellEffects=[];for(let n of this.ripples)this.scene.remove(n.mesh),Yi(n.mesh);this.ripples=[],this.enemy.visible=!0,this.position.set(0,1.75,13),this.startBlend=0,this.yaw=0,this.pitch=0,this.lookTarget=null,this.handUntil=0,this.handMode="idle",this.enemyHit=0,this.shake=0,this.projectiles.forEach(n=>{this.scene.remove(n.mesh,n.trail),Yi(n.mesh),n.trail.geometry.dispose(),n.trail.material.dispose()}),this.projectiles=[],this.particles=[]}}resize(){let e=innerWidth,t=innerHeight;this.camera.aspect=e/t,this.camera.updateProjectionMatrix(),this.viewCamera.aspect=e/t,this.viewCamera.updateProjectionMatrix(),this.renderer.setSize(e,t),this.composer.setSize(e,t)}quality(e){this.renderer.setPixelRatio(Math.min(devicePixelRatio,e?1.6:1)),this.renderer.shadowMap.enabled=e,this.bloom.enabled=e,this.composer.setPixelRatio(this.renderer.getPixelRatio()),this.resize()}update(e,t){let n=e;this.ending.clock.active&&this.ending.clock.frame.still&&(e=0),t.paused||(this.time+=e);let i=this.time,r=t.phase==="combat",a=t.area||0,o=a===1;if(r&&!t.paused){let S=this.yaw,A=pt(Math.sin(S),0,-Math.cos(S)),y=pt(Math.cos(S),0,Math.sin(S));this.position.addScaledVector(y,this.move.x*e*5.8).addScaledVector(A,-this.move.z*e*5.8);let E=[-7,-58,-119+yt.z,-168][a];t.autoAdvance&&t.phase==="combat"&&this.move.lengthSq()===0&&(this.position.z=kt.damp(this.position.z,E,.075,e)),this.position.z=kt.clamp(this.position.z,[-18,-75,-133+yt.z,-181][a],[17,-40,-100+yt.z,-151][a]);let I=o?qn(this.position.z):a===2?yt.x:0;this.position.x=kt.clamp(this.position.x,I+[-11.5,-xt.safeX,-3.5,-11][a],I+[11.5,xt.safeX,3.5,11][a])}let c=t.phase==="travel"&&this.travelArea===2,l=c?Math.min(1,(i-this.travelStart)/this.travelDuration):0;this.journeyProgress=c?l:null;let h=o||t.phase==="travel"&&this.travelArea===1&&this.position.z<-26;this.scene.fog.near=h?65:38,this.scene.fog.far=h?430:140,this.bridgeGroup&&(this.bridgeGroup.visible=a<2&&(!c||l<.75)),this.pavilionPassage.visible=c&&l>.48&&l<.84,this.descentCliff.visible=c&&l>.62||a===2;let u=a===2?1:c?kt.smoothstep(l,.61,.79):0;this.skyDome&&(this.skyDome.position.set(yt.x*u,25+yt.y*u,yt.z*u),this.skyMaterial.opacity=c?1-Math.sin(kt.clamp((l-.49)/.32,0,1)*Math.PI)*.98:1),c&&l>.5&&(this.scene.fog.near=8,this.scene.fog.far=120,this.scene.fog.color.set(7637905)),o&&!c&&(this.position.y=1.75+Ki(this.position.z));let d=t.phase==="ready"?pt(Math.sin(i*.06)*1.7+1,2.7,16):this.position.clone();if(r&&(d.y+=Math.sin(i*(this.move.lengthSq()?11:5))*(this.move.lengthSq()?.045:.012)),t.phase==="travel"){let S=Math.min(1,(i-this.travelStart)/this.travelDuration);if(this.travelArea===1){let A=Kp(this.travelFrom,S);d.set(A.x,A.y,A.z)}else if(this.travelArea===2){let A=Au(this.travelFrom,S);d.set(A.x,A.y,A.z)}else d.copy(this.travelFrom).lerp(this.travelTo,S);this.position.copy(d)}this.camera.position.lerp(d,1-Math.exp(-e*6));let p=c?Au(this.travelFrom,Math.min(1,l+.025)):null,g=c?l<.98?pt(p.x,p.y-.5,p.z):pt(yt.x,yt.y+2,yt.z-125):t.phase==="travel"?pt(this.camera.position.x,this.camera.position.y-.5,this.camera.position.z-16):this.actors?.position(t.targetId)||(a===2?pt(yt.x,yt.y+3,yt.z-125):pt(0,3,[-9,-69,-125,-177][a]));this.lookTarget||=g.clone(),this.lookTarget.lerp(g,1-Math.exp(-e*5));let v=this.lookTarget.clone().add(pt(this.yaw*14,.5+this.pitch*10,0));this.camera.lookAt(v),this.shake=Math.max(0,this.shake-e*.5),t.paused||(this.camera.position.x+=(Qe()-.5)*this.shake,this.camera.position.y+=(Qe()-.5)*this.shake),this.enemy.visible=t.phase==="ready"&&!this.previewPose,this.enemy.position.y=2.7+Math.sin(i*1.3)*.22,this.enemy.rotation.y=Math.sin(i*.6)*.12,this.actors?.update(e,t,i),this.enemyLight&&this.enemyLight.position.copy(g).add(pt(0,1,1)),this.bridgeSeal&&(this.bridgeSeal.rotation.z=-i*.025);for(let S=2;S<4;S++)this.realmGroups?.[S]&&(this.realmGroups[S].visible=a===S||S===2&&c&&l>.64);this.realmRune&&(this.realmRune.rotation.z=i*.04);for(let{g:S,sign:A}of this.gateDoors||[])S.rotation.y=-A*Math.min(1.55,Math.max(0,(i-this.gateOpenAt)*1.15));for(let[S,A]of(this.clouds||[]).entries())A.position.x+=Math.sin(i*.1+S)*.16*e;this.halo.rotation.z=-i*.14,this.halo.material.opacity=.26+(t.incoming?.launched?.15:0),this.halo.material.color.set(t.stage===3?15965289:ci),this.core.rotation.y=i,this.core.rotation.z=i*.4,this.core.scale.setScalar(1+Math.sin(i*3)*.12+(t.incoming?.3:0)),this.aura.material.opacity=t.incoming?.24:.1,this.talismans.forEach((S,A)=>{let y=i*.36+A*hi/8;S.position.set(Math.cos(y)*1.95,.5+Math.sin(y*2)*.5,Math.sin(y)*1.4),S.rotation.set(Math.sin(i+A)*.12,-y+Math.PI/2,Math.sin(y)*.15)}),this.groundSeal.rotation.z=i*.015,this.groundSeal.material.opacity=.3;let f=this.ambient.geometry.attributes.position;for(let S=0;S<this.ambientBase.length;S++){let A=this.ambientBase[S];f.setXYZ(S,A[0]+Math.sin(i*.3+S)*.7,(A[1]+i*.1)%14,A[2]+Math.sin(i*.2+S)*.3)}f.needsUpdate=!0;for(let S of this.particles)t.paused||(S.life-=e,S.p.addScaledVector(S.v,e),S.v.y-=e*1.4);if(this.particles=this.particles.filter(S=>S.life>0),this.particles.forEach((S,A)=>{this.fxPositions.set([S.p.x,S.p.y,S.p.z],A*3);let y=Math.max(0,S.life/S.max);this.fxColors.set([S.color.r*y,S.color.g*y,S.color.b*y],A*3)}),this.fxPoints.geometry.attributes.position.needsUpdate=!0,this.fxPoints.geometry.attributes.color.needsUpdate=!0,this.fxPoints.geometry.setDrawRange(0,this.particles.length),this.projectiles=this.projectiles.filter(S=>{t.paused||(S.age+=e);let A=Math.min(1,S.age/S.life);S.mesh.position.lerpVectors(S.from,S.to,A);let y=S.from.clone().lerp(S.to,Math.max(0,A-.12)),E=S.trail.geometry.attributes.position;return E.setXYZ(0,y.x,y.y,y.z),E.setXYZ(1,S.mesh.position.x,S.mesh.position.y,S.mesh.position.z),E.needsUpdate=!0,A>=1?(this.emitParticles(S.to,S.color,18,3),this.scene.remove(S.mesh,S.trail),Yi(S.mesh),S.trail.geometry.dispose(),S.trail.material.dispose(),!1):!0}),this.ripples=this.ripples.filter(S=>(t.paused||(S.age+=e),S.mesh.scale.setScalar(.4+S.age*.8),S.mesh.material.opacity=Math.max(0,.8-S.age*.55),S.mesh.rotation.z+=e*.25,S.age>1.5?(this.scene.remove(S.mesh),S.mesh.geometry.dispose(),S.mesh.material.dispose(),!1):!0)),Wp(this,t.paused?0:e),this.lakeWater){this.lakeWater.material.roughness=.08+Math.sin(i*.7)*.025;for(let[S,A]of this.waterRipples.entries())A.scale.setScalar(1+Math.sin(i*.6+S)*.09),A.material.opacity=.07+Math.sin(i+S)*.035}Bp(this,t.paused?0:e);let m=this.ending.clock.active,_=!m&&this.handUntil>i?this.handMode:"idle",b=_!=="idle"?_:m?"idle":this.previewPose||this.bandPose||"idle";this.pose(b,t.paused?0:e),this.recoil=kt.damp(this.recoil,0,11,e);let x=_==="guard"?.25:_==="sword"?.26:.33,T=this.outcome==="defeat"?-.9:_==="guard"?-.27:_==="thunder"?-.29:-.3;if(this.handRig.position.x=kt.damp(this.handRig.position.x,x*Math.min(1,this.viewCamera.aspect/1.3),9,e),this.handRig.position.y=kt.damp(this.handRig.position.y,T,9,e)+Math.sin(i*1.6)*.018*e,this.handRig.position.z=-.65+this.recoil,this.handRig.rotation.z=kt.damp(this.handRig.rotation.z,(_==="guard"?-.18:_==="sword"?-.28:.07)+this.bandTilt.roll,10,e),this.handRig.rotation.x=kt.damp(this.handRig.rotation.x,this.bandTilt.pitch,10,e),this.handSigil.material.opacity=0,this.handSigil.rotation.z=i*.8,this.braceletMaterial.emissive.set(53247),this.braceletMaterial.emissiveIntensity=kt.damp(this.braceletMaterial.emissiveIntensity,b==="idle"?2.8:4.1,10,e),this.handLight.intensity=kt.damp(this.handLight.intensity,_==="idle"?0:1.5,6,e),this.guardRing.material.opacity=0,this.guardRing.rotation.z=-i*.15,Fp(this,t),this.renderer.toneMappingExposure=this.outcome==="victory"?1.12+Math.sin(Math.min(1,(i-this.outcomeAt)/2)*Math.PI)*.8:a===3?.86:1.12,this.ending.update(n,t.paused),this.ending.clock.active&&this.ending.clock.frame.scene){this.ending.render();return}this.composer.render(),this.renderer.autoClear=!1,this.renderer.clearDepth(),this.renderer.render(this.viewScene,this.viewCamera),this.renderer.autoClear=!0}diagnostics(){return{webgl:!0,ending:this.ending?.diagnostics,daylight:this.daylight,drawCalls:this.renderer.info.render.calls,triangles:this.renderer.info.render.triangles,failedAssets:[...this.failedAssets],handLoaded:!!this.handModel,handMode:this.handMode,handCurls:[...this.currentCurls||[]],bandPose:this.bandPose,bandTilt:{...this.bandTilt},handRot:[this.handRig.rotation.x,this.handRig.rotation.z],activeSpells:this.spellEffects.length,deathBursts:this.deathBursts?.length||0,handAura:this.auraCast&&this.time-this.auraCast.start<this.auraCast.life?this.auraCast.mode:null,journeyProgress:this.journeyProgress,viewport:[innerWidth,innerHeight],camera:this.camera.position.toArray(),gateAngles:(this.gateDoors||[]).map(e=>e.g.rotation.y)}}};var dm=(s,e,t)=>Math.max(e,Math.min(t,s)),Dc=class{constructor(e=()=>{}){this.emit=e,this.testMode=!1,this.godMode=!1,this.reset()}reset(){Object.assign(this,{phase:"ready",time:0,hp:100,qi:100,area:0,stage:1,boss:0,maxBoss:0,shield:0,guardStart:-99,paused:!1,kills:0,casts:0,swords:0,thunders:0,parries:0,dodges:0,invulnerable:0,outcome:null,targetId:null,travelUntil:0,areaStart:0,combo:0,bestCombo:0,lastHit:-99,autoAdvance:!0}),this.hazard=null,this.nextHazard=0,this.cooldowns={},this.events=[],this.enemies=[],this.pending=[],this.player={x:0,z:13},this.emit({type:"reset"})}start(){return this.phase!=="ready"?!1:(this.phase="combat",this.loadArea(0),this.emit({type:"start"}),!0)}loadArea(e){this.area=e,this.stage=e+1,this.areaStart=this.time,this.enemies=$t[e].enemies.map(t=>({...t,maxHp:t.hp,alive:!0,visible:!1,spawnAt:this.time+t.delay,attackAt:this.time+t.delay+1.8+(["keeper","dragonfly","thunderlord"].includes(t.kind)?.8:0),incoming:null,dodgeUntil:0,dodgeReady:0,revealUntil:0,armored:t.kind==="golem",hits:0,x:t.x,y:["keeper","dragonfly","mirror","thunderlord"].includes(t.kind)?2.8:2.4,z:t.z})),this.targetId=this.enemies[0].id,this.maxBoss=this.enemies.reduce((t,n)=>t+n.maxHp,0),this.refreshHealth(),this.hazard=null,this.nextHazard=this.time+3,this.emit({type:"area",area:e})}log(e){this.events.push({t:+this.time.toFixed(3),...e}),this.events.length>500&&this.events.shift()}refreshHealth(){this.boss=this.enemies.reduce((e,t)=>e+Math.max(0,t.hp),0)}setPlayer(e){e&&Number.isFinite(e.x)&&Number.isFinite(e.z)&&(this.player={x:e.x,z:e.z})}target(){return this.enemies.find(e=>e.id===this.targetId&&e.alive&&e.visible)||this.enemies.find(e=>e.alive&&e.visible)}select(e){return this.enemies.some(t=>t.id===e&&t.alive&&t.visible)?(this.targetId=e,!0):!1}cycleTarget(){let e=this.enemies.filter(n=>n.alive&&n.visible);if(!e.length)return!1;let t=e.findIndex(n=>n.id===this.targetId);return this.select(e[(t+1)%e.length].id)}rejection(e,t=1){return["sword","guard","thunder","dash"].includes(e)?!Number.isFinite(t)||t<.8||t>1?{code:"confidence",message:"\u624B\u5370\u5C1A\u4E0D\u786E\u5B9A\uFF0C\u653E\u677E\u540E\u91CD\u8BD5"}:this.phase==="ready"?{code:"not-started",message:"\u8BF7\u5148\u5165\u573A"}:this.paused?{code:"paused",message:"\u6E38\u620F\u5DF2\u6682\u505C\uFF0C\u8BF7\u7EE7\u7EED\u540E\u51FA\u62DB"}:this.phase==="travel"?{code:"travel",message:"\u672C\u5173\u5DF2\u901A\u8FC7\uFF0C\u6B63\u5728\u524D\u5F80\u4E0B\u4E00\u5173"}:this.phase!=="combat"?{code:"ended",message:"\u8BD5\u70BC\u5DF2\u7ED3\u675F\uFF0C\u8BF7\u91CD\u8BD5"}:!this.testMode&&(this.cooldowns[e]||0)>this.time?{code:"cooldown",message:"\u8FD9\u4E00\u5370\u5C1A\u5728\u51B7\u5374"}:!this.testMode&&fi[e]&&this.qi<fi[e].cost?{code:"mana",message:"\u7075\u529B\u4E0D\u8DB3\uFF0C\u7528\u98DE\u5251\u7B49\u5F85\u56DE\u590D"}:["sword","thunder"].includes(e)&&!this.target()?{code:"approaching",message:"\u7559\u610F\u56DB\u5468\uFF0C\u5996\u5F71\u5C06\u81F3"}:null:{code:"gesture",message:"\u672A\u77E5\u624B\u5370"}}act(e,t="keyboard",n=1){if(this.rejection(e,n))return!1;let i=fi[e];if(this.cooldowns[e]=this.time+(e==="sword"?.42:e==="guard"?1.45:i?.cooldown??1.2),e==="guard"&&(this.shield=this.time+1.05,this.guardStart=this.time,this.area===2)){for(let a of this.enemies)a.revealUntil=this.time+3.5;this.emit({type:"expose"})}e==="dash"&&(this.invulnerable=this.time+.5,this.dodges++);let r=this.target();if(this.log({type:"input",action:e,source:t}),this.emit({type:e,enemyId:r?.id}),e==="sword"||e==="thunder"){if(this.testMode||(this.qi-=i.cost),this.casts++,e==="sword")this.swords++;else{this.thunders++;for(let o of this.enemies)o.visible&&o.armored&&(o.armored=!1,this.emit({type:"armor-break",enemyId:o.id}))}if(e==="sword"&&r.kind==="shade"&&r.dodgeReady<=this.time&&r.hits%3===2)return r.dodgeUntil=this.time+.6,r.dodgeReady=this.time+3,r.attackAt=Math.max(r.attackAt,this.time+.8),this.combo=0,this.emit({type:"enemy-dodge",enemyId:r.id}),!0;let a=e==="thunder"?this.enemies.filter(o=>o.alive&&o.visible):[r];for(let o of a)this.pending.push({enemyId:o.id,amount:e==="thunder"?o.id===r.id?i.damage:Math.round(i.damage*.5):i.damage,at:this.time+(e==="thunder"?.28:.2),stagger:e==="thunder"?1.15:.12})}return!0}damage(e,t=this.target()?.id,n=0){let i=this.enemies.find(o=>o.id===t);if(!i?.alive||this.phase!=="combat")return;let r=["mirror","reflection"].includes(i.kind)&&i.revealUntil<=this.time;(r||i.armored)&&(e=Math.max(1,Math.round(e*.2)),this.emit({type:"resist",enemyId:i.id,reason:r?"mirror":"armor"})),i.hp=Math.max(0,i.hp-e),i.hits++,this.area===1&&i.kind==="dragonfly"&&i.hits%3===0&&(i.incoming=null,i.attackAt=this.time+1.2,this.emit({type:"interrupt",enemyId:i.id})),this.combo=this.time-this.lastHit<2.4?this.combo+1:1,this.lastHit=this.time,this.bestCombo=Math.max(this.bestCombo,this.combo),n>0&&(i.attackAt=Math.max(i.attackAt,this.time+n),n>.5&&(i.incoming=null)),this.emit({type:"enemy-hit",enemyId:i.id,amount:e}),i.hp===0&&(i.alive=!1,i.incoming=null,this.kills++,this.qi=dm(this.qi+10,0,100),this.emit({type:"enemy-killed",enemyId:i.id}),this.log({type:"kill",enemyId:i.id}),i.id===this.targetId&&(this.targetId=this.enemies.find(o=>o.alive&&o.visible)?.id||null)),this.refreshHealth(),this.enemies.every(o=>!o.alive)&&(this.pending=[],this.area<$t.length-1?(this.phase="travel",this.travelDuration=Yp(this.area),this.travelUntil=this.time+this.travelDuration,this.emit({type:"travel",area:this.area+1,duration:this.travelDuration})):(this.phase="victory",this.outcome="\u8BD5\u70BC\u6210\u529F",this.hazard=null,this.emit({type:"finish",enemyId:i.id}),this.log({type:"finish",source:"last-enemy"})))}update(e){if(this.paused||!["combat","travel"].includes(this.phase))return;if(e=dm(Number.isFinite(e)?e:0,0,.1),this.time+=e,this.qi=Math.min(100,this.qi+e*8),this.phase==="travel"){this.time>=this.travelUntil&&(this.hp=Math.min(100,this.hp+25),this.qi=Math.min(100,this.qi+25),this.phase="combat",this.player={...$t[this.area+1].camera},this.loadArea(this.area+1));return}if(this.phase!=="combat")return;let t=this.pending.filter(n=>n.at<=this.time);this.pending=this.pending.filter(n=>n.at>this.time);for(let n of t)if(this.damage(n.amount,n.enemyId,n.stagger),this.phase!=="combat")return;for(let[n,i]of this.enemies.entries()){if(!i.alive)continue;if(!i.visible){if(this.time<i.spawnAt)continue;i.visible=!0,this.emit({type:"spawn",enemyId:i.id,kind:i.kind}),this.target()||(this.targetId=i.id)}let r=this.time-i.spawnAt,a=$t[this.area].enemies[n],o=i.dodgeUntil>this.time;if(i.x=a.x+Math.sin(r*(i.kind==="shade"?1.9:.65)+n)*(["keeper","thunderlord","golem"].includes(i.kind)?1.4:2.7)+(o?Math.sin((.6-i.dodgeUntil+this.time)/.6*Math.PI)*3.2:0),i.y=($t[this.area].camera.y?$t[this.area].camera.y-1.75:0)+(["keeper","dragonfly","mirror","thunderlord"].includes(i.kind)?2.8:2.1)+Math.sin(r*(["wisp","manta","phoenix"].includes(i.kind)?2.4:1.1)+n)*(["wisp","manta","phoenix"].includes(i.kind)?1.1:.42),i.kind==="dragonfly"&&(i.x+=Math.sin(r*3.8)*2,i.y+=Math.sin(r*4)*.45),i.z=a.z+Math.sin(r*.7+n)*(["wisp","manta","phoenix"].includes(i.kind)?2.2:1.1),!i.incoming&&this.time>=i.attackAt&&(i.incoming={start:this.time,release:this.time+.7,hit:this.time+1.35,launched:!1},this.emit({type:"warning",enemyId:i.id})),i.incoming&&!i.incoming.launched&&this.time>=i.incoming.release&&(i.incoming.launched=!0,this.emit({type:"enemy-cast",enemyId:i.id})),i.incoming&&this.time>=i.incoming.hit){if(i.incoming=null,i.attackAt=this.time+(["keeper","dragonfly","thunderlord"].includes(i.kind)?3:3.9)+n*.2,this.invulnerable>this.time){this.emit({type:"evade",enemyId:i.id});continue}if(this.shield>this.time){let c=this.time-this.guardStart<=.32;this.parries++,this.qi=Math.min(100,this.qi+8),this.emit({type:c?"parry":"block",enemyId:i.id}),c&&this.damage(48,i.id,.9)}else if(this.godMode||(this.hp=Math.max(0,this.hp-(["keeper","dragonfly","thunderlord"].includes(i.kind)?19:12))),this.combo=0,this.emit({type:"hit",enemyId:i.id}),!this.hp){this.phase="defeat",this.outcome="\u8BD5\u70BC\u5931\u8D25",this.pending=[],this.emit({type:"defeat"}),this.log({type:"defeat"});return}if(this.phase!=="combat")return}}this.updateHazard()}updateHazard(){if(!(this.area!==3||this.phase!=="combat")&&(!this.hazard&&this.time>=this.nextHazard&&(this.hazard={x:this.player.x,z:this.player.z,hit:this.time+1.5,radius:2.5},this.emit({type:"hazard-warning",position:{...this.hazard}})),this.hazard&&this.time>=this.hazard.hit)){let e=this.hazard;if(this.hazard=null,this.nextHazard=this.time+4.5,this.emit({type:"hazard-strike",position:e}),Math.hypot(this.player.x-e.x,this.player.z-e.z)>e.radius||this.invulnerable>this.time){this.emit({type:"evade"});return}if(this.shield>this.time){this.parries++,this.emit({type:"block"});return}this.godMode||(this.hp=Math.max(0,this.hp-17)),this.emit({type:"hit"}),this.hp||(this.phase="defeat",this.outcome="\u8BD5\u70BC\u5931\u8D25",this.pending=[],this.emit({type:"defeat"}))}}snapshot(){let e=this.target();return{phase:this.phase,time:this.time,hp:this.hp,qi:this.qi,boss:this.boss,maxBoss:this.maxBoss,stage:this.stage,area:this.area,areaName:$t[this.area].name,paused:this.paused,shield:this.shield,incoming:this.enemies.filter(t=>t.incoming).map(t=>({...t.incoming,enemyId:t.id})).sort((t,n)=>t.hit-n.hit)[0]||null,casts:this.casts,swords:this.swords,thunders:this.thunders,parries:this.parries,dodges:this.dodges,kills:this.kills,totalEnemies:jp,hazard:this.hazard?{...this.hazard}:null,combo:this.combo,bestCombo:this.bestCombo,targetId:e?.id||null,target:e?{id:e.id,name:e.name,hp:e.hp,maxHp:e.maxHp}:null,enemies:this.enemies.map(t=>({id:t.id,kind:t.kind,name:t.name,hp:t.hp,maxHp:t.maxHp,alive:t.alive,visible:t.visible,x:t.x,y:t.y,z:t.z,dodging:t.dodgeUntil>this.time,shielded:["mirror","reflection"].includes(t.kind)&&t.revealUntil<=this.time||t.armored,incoming:t.incoming?{...t.incoming}:null})),cooldowns:{...this.cooldowns},autoAdvance:this.autoAdvance}}};var _M=new Set(["off","link","live","paused"]),yM=new Set(["","sword","guard","thunder"]),vM=new Set(["ok","mask","bad",""]);function mm(s){if(!s||!_M.has(s.state)||typeof s.text!="string"||!yM.has(s.pose??""))return null;let e=Array.isArray(s.acc)&&s.acc.length===3&&s.acc.every(Number.isFinite)&&Math.hypot(...s.acc)>0?s.acc:null,t=Array.isArray(s.lanes)&&s.lanes.length===8&&s.lanes.every(i=>vM.has(i))?[...s.lanes]:null,n=i=>typeof i=="string"?i.slice(0,40):"";return{state:s.state,text:s.text.slice(0,40),pose:s.pose||"",acc:e,lanes:t,signal:n(s.signal),rec:n(s.rec)}}var fm=s=>{let e=Math.hypot(...s);return s.map(t=>t/e)},Uc={pitch:[1,1],roll:[0,-1]},pm=.7;function gm(s,e){let t=fm(s),n=fm(e),i=[t[1]*n[2]-t[2]*n[1],t[2]*n[0]-t[0]*n[2],t[0]*n[1]-t[1]*n[0]],r=a=>Math.max(-pm,Math.min(pm,a));return{pitch:r(Math.asin(Math.max(-1,Math.min(1,i[Uc.pitch[0]])))*Uc.pitch[1]),roll:r(Math.asin(Math.max(-1,Math.min(1,i[Uc.roll[0]])))*Uc.roll[1])}}var xs=[{gesture:"sword",name:"\u9053\u6307\u5251",mark:"\u5251",key:"Q",line:"\u8BA9\u7B2C\u4E00\u7F15\u5251\u610F\uFF0C\u542C\u4ECE\u4F60\u7684\u610F\u5FD7\u3002",pose:"\u638C\u5FC3\u671D\u4E0A\uFF0C\u4F38\u51FA\u98DF\u6307\u4E0E\u5C0F\u6307\uFF0C\u4E2D\u6307\u3001\u65E0\u540D\u6307\u5F2F\u4E0B\uFF0C\u62C7\u6307\u538B\u5728\u5B83\u4EEC\u7684\u6307\u7532\u4E0A\u3002",effect:"\u98DE\u5251\u51FA\u9798 \xB7 \u6301\u7EED\u8FDB\u653B",hint:"\u653E\u677E\uFF0C\u518D\u7ED3\u5370\u3002"},{gesture:"guard",name:"\u7834\u90AA\u5370",mark:"\u5370",key:"E",line:"\u8FD9\u53EA\u624B\uFF0C\u4E5F\u53EF\u4EE5\u9009\u62E9\u5B88\u62A4\u3002",pose:"\u624B\u80CC\u671D\u4E0A\uFF0C\u98DF\u6307\u3001\u4E2D\u6307\u5E76\u62E2\u4F38\u76F4\uFF0C\u65E0\u540D\u6307\u3001\u5C0F\u6307\u5F2F\u4E0B\uFF0C\u62C7\u6307\u4ECE\u4FA7\u9762\u538B\u4F4F\u5F2F\u4E0B\u7684\u4E24\u6307\u3002",effect:"\u7ED3\u9635\u62A4\u8EAB \xB7 \u8FCE\u51FB\u53CD\u5236",hint:"\u4E0D\u8981\u7528\u529B\u7EF7\u7D27\u3002\u8BA4\u51FA\u624B\u5370\u540E\uFF0C\u5148\u56DE\u5230\u653E\u677E\u3002"},{gesture:"thunder",name:"\u4E94\u96F7\u8BC0",mark:"\u96F7",key:"R",line:"\u96F7\u4ECE\u638C\u8D77\uFF0C\u5374\u4E0D\u7531\u5929\u547D\u3002",pose:"\u624B\u80CC\u671D\u4E0A\uFF0C\u56DB\u6307\u63E1\u7D27\uFF0C\u62C7\u6307\u5728\u62F3\u5916\u6A2A\u6263\u5728\u98DF\u6307\u3001\u4E2D\u6307\u4E0A\uFF0C\u4E0E\u672C\u6B21\u6821\u51C6\u4E00\u81F4\u3002",effect:"\u96F7\u7B26\u843D\u4E0B \xB7 \u91CD\u51FB\u9547\u90AA",hint:"\u52A8\u4F5C\u6E05\u695A\u5373\u53EF\uFF0C\u4E0D\u5FC5\u63E1\u5F97\u66F4\u7D27\u3002"}],id=4,Hs=1,sd=[{kicker:"\u4E94\u624B\u5B9A\u5929",title:"\u5929\u6709\u4E94\u624B\u3002\u6267\u638C\u8BF8\u5929\u3002",text:"\u4E94\u53EA\u5DE8\u624B\uFF0C\u66FE\u7EF4\u7CFB\u4E16\u754C\u7684\u79E9\u5E8F\u3002",visual:"order"},{kicker:"\u8BF8\u5929\u5931\u5E8F",title:"\u8BF8\u5929\u5D29\u584C\u3002\u4E00\u624B\u5165\u4F60\u3002",text:"\u4F60\u7684\u53F3\u624B\u6B63\u5728\u795E\u5316\u3002\u8155\u4E0A\u7684\u73AF\uFF0C\u662F\u6700\u540E\u4E00\u9053\u9501\u3002",visual:"fall"},{kicker:"\u638C\u5FC3\u4E4B\u95EE",title:"\u795E\u9501\u5C06\u88C2\u3002\u8C01\u5728\u638C\u8C01\uFF1F",text:"\u6765\u8005\u672A\u5FC5\u4E3A\u6740\u4F60\u3002\u5148\u8BA9\u8FD9\u53EA\u624B\uFF0C\u542C\u4F60\u7684\u3002",visual:"wake"}],Oc=class{constructor(){this.close()}close(){this.phase="closed",this.mode="hardware",this.chapter=0,this.storyTime=0,this.worn=!1,this.stableSince=null,this.bandAt=-1/0,this.band=null,this.counts=[0,0,0],this.lesson=0,this.armed=!1,this.restSince=null,this.lastKey=-1/0,this.message=""}start(){this.close(),this.phase="story"}nextStory(){this.phase==="story"&&(this.chapter<sd.length-1?(this.chapter++,this.storyTime=0):this.toWear())}toWear(){this.phase="wear",this.storyTime=0,this.message=""}useKeyboard(){this.mode="keyboard",this.beginPractice()}chooseHardware(){this.mode="hardware",this.worn=!1,this.counts=[0,0,0],this.lesson=0,this.toWear()}setWorn(e){this.worn=!!e}updateBand(e,t){t-this.bandAt>1500&&(this.stableSince=null,this.restSince=null,this.armed=!1),this.band=e,this.bandAt=t,this.healthy(t)?(this.stableSince??=t,!e.pose&&/放松|rest/i.test(e.text)?(this.restSince??=t,t-this.restSince>=300&&(this.armed=!0)):this.restSince=null):(this.stableSince=null,this.restSince=null,this.armed=!1),this.checkConnection(t)}healthy(e){return!!this.band&&e-this.bandAt<=1500&&this.band.state==="live"&&!/数据过期|数据中断|信号不连续|同步屏蔽/.test(this.band.text)&&Array.isArray(this.band.lanes)&&this.band.lanes.length===8&&this.band.lanes.includes("ok")&&this.band.lanes.every(t=>t==="ok"||t==="mask")}wearReady(e){return this.worn&&this.healthy(e)&&this.stableSince!==null&&e-this.stableSince>=2e3}beginPractice(e){return this.mode==="hardware"&&!this.wearReady(e)?!1:(this.phase="practice",this.counts=[0,0,0],this.lesson=0,this.armed=!1,this.restSince=null,this.message=this.mode==="hardware"?"\u5148\u653E\u677E\u624B\u6307\uFF0C\u7B49\u753B\u9762\u63D0\u793A\u540E\u518D\u7ED3\u5370\u3002":"\u952E\u76D8\u7EC3\u4E60\uFF1A\u6309\u63D0\u793A\u6309\u952E\uFF0C\u6BCF\u4E2A\u624B\u5370\u8BD5\u4E00\u6B21\u3002",!0)}checkConnection(e){this.mode==="hardware"&&["practice","ready"].includes(this.phase)&&!this.healthy(e)&&(this.phase="wear",this.counts=[0,0,0],this.lesson=0,this.worn=!1,this.stableSince=null,this.armed=!1,this.restSince=null,this.message="\u4FE1\u53F7\u4E2D\u65AD\u6216\u68C0\u67E5\u672A\u901A\u8FC7\u3002\u8BF7\u56DE\u5230\u8BC6\u522B\u9875\u68C0\u67E5\uFF0C\u518D\u91CD\u65B0\u5F00\u59CB\u3002")}tick(e,t,n=!1){this.phase==="story"&&!n&&(this.storyTime+=e,this.storyTime>=id&&this.nextStory()),this.healthy(t)||(this.stableSince=null,this.restSince=null,this.armed=!1),this.checkConnection(t)}input(e,t,n,i){if(this.phase!=="practice")return{accepted:!1,code:"onboarding",message:"\u8BF7\u5148\u5B8C\u6210\u5F53\u524D\u5F15\u5BFC"};if(!xs.some(o=>o.gesture===e)||!Number.isFinite(n)||n<.8||n>1)return{accepted:!1,code:"confidence",message:"\u624B\u5370\u5C1A\u4E0D\u786E\u5B9A\uFF0C\u653E\u677E\u540E\u91CD\u8BD5"};if(this.checkConnection(i),this.phase!=="practice")return{accepted:!1,code:"band-offline",message:this.message};if(this.counts[this.lesson]>=Hs)return{accepted:!1,code:"practice-complete",message:"\u8FD9\u4E00\u5370\u5DF2\u5B8C\u6210\uFF0C\u8BF7\u9009\u62E9\u4E0B\u4E00\u5370"};let r=t==="gesture-adapter";if(this.mode==="hardware"!==r)return{accepted:!1,code:"input-mode",message:this.mode==="hardware"?"\u5F53\u524D\u4E3A\u624B\u73AF\u68C0\u67E5\uFF0C\u8BF7\u7528\u771F\u5B9E\u624B\u5370":"\u5F53\u524D\u4E3A\u952E\u76D8\u7EC3\u4E60\uFF0C\u624B\u73AF\u68C0\u67E5\u5C1A\u672A\u5B8C\u6210"};if(r&&!this.armed)return{accepted:!1,code:"relax",message:"\u5148\u653E\u677E\u81F3\u5C11\u7247\u523B\uFF0C\u518D\u505A\u4E00\u6B21\u624B\u5370"};if(!r&&i-this.lastKey<300)return{accepted:!1,code:"practice-wait",message:"\u677E\u5F00\u6309\u952E\uFF0C\u518D\u8BD5\u4E00\u6B21"};r?(this.armed=!1,this.restSince=null):this.lastKey=i;let a=xs[this.lesson].gesture;return e!==a?(this.message=`\u8FD9\u6B21\u662F${xs.find(o=>o.gesture===e).name}\uFF0C\u8BF7\u8BD5${xs[this.lesson].name}\u3002`,{accepted:!1,code:"practice-other",message:this.message}):(this.counts[this.lesson]++,this.message="\u8FD9\u4E00\u5370\u5DF2\u54CD\u5E94\u3002",{accepted:!0,code:"practice",message:`${xs[this.lesson].name}\u7EC3\u4E60\u5DF2\u54CD\u5E94`,practice:!0})}nextLesson(){return this.phase!=="practice"||this.counts[this.lesson]<Hs?!1:(this.armed=!1,this.restSince=null,this.lastKey=-1/0,this.lesson<2?(this.lesson++,this.message=this.mode==="hardware"?"\u5148\u653E\u677E\uFF0C\u518D\u8BD5\u8FD9\u4E00\u5370\u3002":"\u6309\u63D0\u793A\u6309\u952E\uFF0C\u5404\u8BD5\u4E00\u5370\u3002"):this.phase="ready",!0)}canFinish(e){return this.phase==="ready"&&this.counts.every(t=>t>=Hs)&&(this.mode==="keyboard"||this.wearReady(e))}snapshot(e){return{phase:this.phase,mode:this.mode,chapter:this.chapter,storyTime:this.storyTime,lesson:this.lesson,counts:[...this.counts],armed:this.armed,worn:this.worn,healthy:this.healthy(e),stableMs:this.stableSince===null?0:Math.max(0,e-this.stableSince),wearReady:this.wearReady(e),canFinish:this.canFinish(e),message:this.message}}};var ke=s=>document.getElementById(s);function xm({preview:s,startCombat:e,onOpen:t,onClose:n}){let i=new Oc,r="",a=-1,o=-1,c=0,l=null,h=matchMedia("(prefers-reduced-motion: reduce)").matches;function u(v=performance.now()){let f=i.snapshot(v),m=f.phase!=="closed";if(ke("journey").hidden=!m,!m){s("");return}ke("journey").dataset.phase=f.phase,document.querySelectorAll("[data-journey-step]").forEach(_=>{let b=["story","wear","practice","ready"];_.dataset.current=String(_.dataset.journeyStep===f.phase),_.dataset.done=String(b.indexOf(_.dataset.journeyStep)<b.indexOf(f.phase))});for(let _ of["story","wear","practice","ready"])ke(`j-${_}`).hidden=f.phase!==_;if(f.phase==="story"){let _=sd[f.chapter];ke("story-kicker").textContent=_.kicker,ke("story-title").textContent=_.title,ke("story-copy").textContent=_.text,ke("story-art").dataset.visual=_.visual,ke("story-number").textContent=`0${f.chapter+1} / 03`,ke("story-progress").style.width=`${Math.min(100,f.storyTime/id*100)}%`,ke("story-next").textContent=f.chapter===2?"\u68C0\u67E5\u795E\u9501 \u2192":"\u7EE7\u7EED \u2192",a!==f.chapter&&(ke("j-story").classList.remove("enter"),ke("j-story").offsetWidth,ke("j-story").classList.add("enter"),a=f.chapter)}if(f.phase==="wear"){ke("wear-confirm").checked=f.worn,ke("wear-continue").disabled=!f.wearReady,ke("wear-bar").style.width=`${Math.min(100,f.stableMs/2e3*100)}%`;let _=i.band;ke("wear-status").textContent=f.wearReady?"\u795E\u9501\u5DF2\u56DE\u5E94 \xB7 \u53EF\u5F00\u59CB\u8BD5\u5370":f.healthy?f.worn?"\u4FDD\u6301\u653E\u677E\uFF0C\u6B63\u5728\u89C2\u5BDF\u4FE1\u53F7\u2026":"\u4FE1\u53F7\u5DF2\u5230\u8FBE\uFF0C\u8BF7\u786E\u8BA4\u4F69\u6234\u4F4D\u7F6E":_?.state==="link"?"\u624B\u73AF\u5DF2\u8FDE\u63A5 \xB7 \u8BF7\u5728 App \u5F00\u59CB\u7ED3\u5370\u8BC6\u522B":_?.state==="paused"?"\u4FE1\u53F7\u68C0\u67E5\u6682\u505C \xB7 \u8BF7\u67E5\u770B\u8BC6\u522B\u9875":"\u7B49\u5F85 OpenEMG App \u7684\u5B9E\u65F6\u4FE1\u53F7",ke("wear-signal").textContent=f.healthy?_.signal||"\u6B63\u5728\u63A5\u6536\u516B\u8DEF\u72B6\u6001":f.message||_?.signal||"\u5728 OpenEMG App \u5B8C\u6210\u300C\u8FDE\u4E0A \u2192 \u6234\u597D \u2192 \u6821\u51C6\u300D\uFF0C\u9009\u62E9\u300C\u7ED3\u5370\u4E09\u62DB\u300D\u5E76\u4FDD\u6301\u8BC6\u522B\u9875\u5F00\u542F\u3002",ke("wear-lanes").replaceChildren(...Array.from({length:8},(b,x)=>{let T=document.createElement("span");return T.dataset.lane=v-i.bandAt<=1500&&_?.lanes?.[x]||"",T.textContent=String(x+1),T}))}if(f.phase==="practice"){let _=xs[f.lesson];document.querySelectorAll("[data-seal]").forEach(x=>{x.dataset.current=String(x.dataset.seal===_.gesture)}),ke("lesson-number").textContent=`0${f.lesson+1} / 03`,ke("lesson-name").textContent=_.name,ke("lesson-line").textContent=_.line,ke("lesson-pose").textContent=_.pose,ke("lesson-effect").textContent=_.effect,ke("lesson-hint").textContent=_.hint,ke("lesson-mode").textContent=f.mode==="hardware"?"\u771F\u5B9E\u624B\u73AF \xB7 \u8BC6\u522B\u54CD\u5E94\u68C0\u67E5":"\u952E\u76D8\u7EC3\u4E60 \xB7 \u4E0D\u8BA1\u4E3A\u624B\u73AF\u8BC6\u522B\u901A\u8FC7",ke("lesson-key").textContent=_.key,ke("practice-key").textContent=`\u6309 ${_.key} \xB7 ${_.name}`,ke("practice-key").hidden=f.mode!=="keyboard",ke("lesson-next").disabled=f.counts[f.lesson]<Hs,ke("lesson-next").textContent=f.lesson===2?"\u5B8C\u6210\u4E09\u5370 \u2192":"\u4E0B\u4E00\u5370 \u2192",ke("lesson-counter").textContent=`${f.counts[f.lesson]} / ${Hs}`,document.querySelectorAll("[data-lesson-dot]").forEach((x,T)=>x.dataset.done=String(f.counts[f.lesson]>T));let b=i.band;ke("lesson-live").textContent=f.mode==="hardware"?b?.rec||b?.text||"\u7B49\u5F85\u8BC6\u522B":"\u8BF7\u6309\u63D0\u793A\u6309\u952E\uFF0C\u6216\u70B9\u51FB\u7EC3\u4E60\u6309\u94AE",v>=c&&(ke("lesson-status").textContent=f.message||"\u5148\u653E\u677E\uFF0C\u518D\u7ED3\u5370\u3002"),ke("lesson-relax").textContent=f.counts[f.lesson]>=Hs?"\u8FD9\u4E00\u5370\u5DF2\u5B8C\u6210":f.mode==="hardware"?f.armed?"\u53EF\u4EE5\u7ED3\u5370\u4E86":"\u5148\u653E\u677E\u624B\u6307":"\u6309\u63D0\u793A\u5B8C\u6210\u8FD9\u4E00\u5370",(o!==f.lesson||r!==f.phase)&&(o=f.lesson,s(_.gesture))}else s("");f.phase==="ready"&&(ke("ready-mode").textContent=f.mode==="hardware"?"\u795E\u9501\u4FE1\u53F7\u4E0E\u4E09\u5370\u54CD\u5E94\u5DF2\u68C0\u67E5":"\u952E\u76D8\u7EC3\u4E60\u5B8C\u6210 \xB7 \u624B\u73AF\u5C1A\u672A\u68C0\u67E5",ke("ready-description").textContent=f.mode==="hardware"?"\u4E09\u5370\u5DF2\u5E94\u3002\u4EE5\u5251\u8FDB\u653B\uFF0C\u4EE5\u5370\u62A4\u8EAB\uFF0C\u4EE5\u96F7\u9547\u90AA\u3002":"Q \u5251 \xB7 E \u5370 \xB7 R \u96F7\u3002\u952E\u76D8\u7EC3\u4E60\u5DF2\u5B8C\u6210\uFF0C\u624B\u73AF\u5C1A\u672A\u68C0\u67E5\u3002",ke("enter-trial").disabled=!f.canFinish,ke("ready-hardware").hidden=f.mode==="hardware"),r=f.phase}function d(){t(),i.start(),r="",a=-1,o=-1,c=0,l=null,u(),ke("journey-close").focus()}function p(){i.close(),s(""),u(),n()}ke("journey-close").onclick=p,ke("story-next").onclick=()=>{i.nextStory(),u()},ke("story-skip").onclick=()=>{i.toWear(),u()},ke("wear-confirm").onchange=v=>{i.setWorn(v.target.checked),u()},ke("wear-continue").onclick=()=>{i.beginPractice(performance.now()),u()},ke("wear-keyboard").onclick=()=>{i.useKeyboard(),u()},ke("practice-key").onclick=()=>g(xs[i.lesson].gesture,"touch",1),ke("lesson-next").onclick=()=>{i.nextLesson(),l=null,u()},ke("lesson-back").onclick=()=>{i.chooseHardware(),u()},ke("ready-hardware").onclick=()=>{i.chooseHardware(),u()},ke("enter-trial").onclick=()=>{if(i.canFinish(performance.now())){let v=i.mode;i.close(),s(""),u(),e(v)}};function g(v,f,m){let _=i.input(v,f,m,performance.now());return _.accepted?(l=performance.now(),s(v,!0),ke("lesson-status").textContent=i.message,c=0):i.phase==="practice"&&(ke("lesson-status").textContent=_.message,c=performance.now()+1800),u(),_}return{open:d,close:p,input:g,band(v){i.updateBand(v,performance.now()),u()},tick(v){let f=performance.now();i.tick(v,f,h),i.phase==="practice"&&l!==null&&f-l>=1100&&(i.nextLesson(),l=null),u()},get active(){return i.phase!=="closed"},get phase(){return i.phase},snapshot:()=>i.snapshot(performance.now())}}var MM=[{name:"\u5C71\u95E8 \xB7 \u949F\u9F13",bpm:116,root:50,notes:[62,69,74,76,81,79,76,74],ambience:"mountain"},{name:"\u60AC\u6865 \xB7 \u51CC\u98CE",bpm:150,root:52,notes:[64,67,71,74,76,71,67,64],ambience:"wind"},{name:"\u955C\u6E56 \xB7 \u6C34\u541F",bpm:106,root:53,notes:[65,69,72,74,77,74,72,69],ambience:"water"},{name:"\u96F7\u72F1 \xB7 \u6218\u9F13",bpm:164,root:48,notes:[60,63,67,70,72,70,67,63],ambience:"storm"}],Bc=class{constructor(){this.enabled=!0,this.mode="explore",this.context=null,this.step=0,this.nextBeat=0,this.voices=0,this.scene=0,this.ambient=[],this.hidden=!1}setHidden(e){this.hidden=e,this.context&&(e?this.context.suspend().catch(()=>{}):this.enabled&&this.context.resume().catch(()=>{}))}async unlock(){if(!this.context){let e=window.AudioContext||window.webkitAudioContext;if(!e)return;let t=this.context=new e;this.master=t.createGain(),this.master.gain.value=.52;let n=t.createDynamicsCompressor();n.threshold.value=-19,n.ratio.value=5,this.master.connect(n),n.connect(t.destination),this.space=t.createConvolver();let i=t.sampleRate*2.8,r=t.createBuffer(2,i,t.sampleRate);for(let o=0;o<2;o++){let c=r.getChannelData(o);for(let l=0;l<i;l++)c[l]=(Math.random()*2-1)*Math.pow(1-l/i,3)*.27}this.space.buffer=r;let a=t.createGain();a.gain.value=.3,this.space.connect(a),a.connect(this.master),this.regularBus=t.createGain(),this.regularBus.connect(this.master),this.regularBus.connect(this.space),this.finaleBus=t.createGain(),this.finaleBus.connect(this.master),this.finaleBus.connect(this.space),this.endingMix=null,this.buildAmbience(),this.nextBeat=t.currentTime+.15,this.timer=setInterval(()=>this.schedule(),90)}this.hidden?await this.context.suspend().catch(()=>{}):this.enabled&&await this.context.resume()}setEnabled(e){this.enabled=e,this.context&&(this.master.gain.setTargetAtTime(e&&this.mode!=="silent"?.52:0,this.context.currentTime,.07),e&&!this.hidden&&this.context.resume(),this.mixAmbience())}setMode(e){this.mode!==e&&(this.mode=e,this.context&&(this.nextBeat=Math.max(this.nextBeat,this.context.currentTime+.06),this.master.gain.setTargetAtTime(this.enabled&&e!=="silent"?.52:0,this.context.currentTime,.1),this.mixAmbience()))}setScene(e){this.scene!==e&&(this.scene=Math.max(0,Math.min(3,e)),this.step=0,this.context&&(this.nextBeat=this.context.currentTime+.08,this.mixAmbience()))}buildAmbience(){let e=this.context,t=e.sampleRate*4,n=e.createBuffer(1,t,e.sampleRate),i=n.getChannelData(0),r=0;for(let a=0;a<t;a++){let o=Math.random()*2-1;r=(r+.018*o)/1.018,i[a]=r*2.8+o*.08}for(let a=0;a<4;a++){let o=e.createBufferSource();o.buffer=n,o.loop=!0;let c=e.createBiquadFilter();c.type=a===2?"lowpass":"bandpass",c.frequency.value=[650,1100,2300,180][a],c.Q.value=.55;let l=e.createGain();l.gain.value=0,o.connect(c),c.connect(l),l.connect(this.master),o.start(),this.ambient.push({source:o,filter:c,gain:l})}this.mixAmbience()}mixAmbience(){if(this.context)for(let[e,t]of this.ambient.entries())t.gain.gain.setTargetAtTime(["silent","outcome"].includes(this.mode)||!this.enabled?0:e===this.scene?[.22,.48,.7,.42][e]:0,this.context.currentTime,.55)}strings(e,t,n=2.2,i=.025){let r=this.context;for(let[a,o]of e.entries()){let c=r.createOscillator(),l=r.createOscillator(),h=r.createGain(),u=r.createBiquadFilter();c.type=l.type="sawtooth",c.frequency.value=440*2**((o-69)/12),l.frequency.value=c.frequency.value,c.detune.value=-5,l.detune.value=5,u.type="lowpass",u.frequency.value=850+a*150,u.Q.value=.6,h.gain.setValueAtTime(0,t),h.gain.linearRampToValueAtTime(i,t+.3),h.gain.setTargetAtTime(1e-4,t+n-.6,.18),c.connect(u),l.connect(u),u.connect(h),this.bus(h,1,t,(a-1)*.25),c.start(t),l.start(t),c.stop(t+n),l.stop(t+n),c.onended=()=>{c.disconnect(),l.disconnect(),u.disconnect(),h.disconnect()}}}waterDrop(e,t=.05,n=0){let i=this.context,r=i.createOscillator(),a=i.createGain();r.frequency.setValueAtTime(1050,e),r.frequency.exponentialRampToValueAtTime(390,e+.13),a.gain.setValueAtTime(t,e),a.gain.exponentialRampToValueAtTime(1e-4,e+.32),r.connect(a),this.bus(a,1,e,n),r.start(e),r.stop(e+.34),r.onended=()=>{r.disconnect(),a.disconnect()}}bus(e,t,n,i=0){let r=this.context,a=r.createGain(),o=r.createStereoPanner();return a.gain.value=t,o.pan.value=i,e.connect(a),a.connect(o),o.connect(this.cinematicVoice?this.finaleBus:this.regularBus),setTimeout(()=>{a.disconnect(),o.disconnect()},4e3),a}pluck(e,t,n=.12,i=0,r=1.4){let a=this.context,o=440*Math.pow(2,(e-69)/12),c=Math.max(2,Math.round(a.sampleRate/o)),l=Math.ceil(a.sampleRate*r),h=a.createBuffer(1,l,a.sampleRate),u=h.getChannelData(0);for(let g=0;g<c;g++)u[g]=(Math.random()*2-1)*.8;for(let g=c;g<l;g++)u[g]=(u[g-c]+u[g-c+1])*.496;let d=a.createBufferSource();d.buffer=h;let p=a.createBiquadFilter();p.type="lowpass",p.frequency.value=4200,d.connect(p),this.bus(p,n,t,i),d.start(t),d.onended=()=>{d.disconnect(),p.disconnect()}}flute(e,t,n=1,i=.05){let r=this.context,a=440*Math.pow(2,(e-69)/12),o=r.createOscillator(),c=r.createOscillator(),l=r.createBufferSource(),h=r.createGain(),u=r.createOscillator(),d=r.createGain();o.type="sine",o.frequency.value=a,c.type="sine",c.frequency.value=a*2;let p=r.createGain();p.gain.value=.12,c.connect(p),p.connect(h),o.connect(h),u.frequency.value=4.7,d.gain.value=2.2,u.connect(d),d.connect(o.frequency);let g=r.createBuffer(1,Math.ceil(r.sampleRate*n),r.sampleRate),v=g.getChannelData(0);for(let m=0;m<v.length;m++)v[m]=(Math.random()*2-1)*.12;l.buffer=g;let f=r.createBiquadFilter();f.type="bandpass",f.frequency.value=a*2,f.Q.value=1.4,l.connect(f),f.connect(h),h.gain.setValueAtTime(0,t),h.gain.linearRampToValueAtTime(i,t+.09),h.gain.setTargetAtTime(i*.75,t+.14,.25),h.gain.setTargetAtTime(0,t+n-.15,.06),this.bus(h,1,t,Math.sin(e)*.3),o.start(t),c.start(t),l.start(t),u.start(t),o.stop(t+n+.1),c.stop(t+n+.1),u.stop(t+n+.1),l.onended=()=>{o.disconnect(),c.disconnect(),l.disconnect(),f.disconnect(),h.disconnect(),u.disconnect(),d.disconnect(),p.disconnect()}}gong(e,t=.12,n=110){let i=this.context;for(let[r,a]of[1,1.48,2.07,2.91,4.16].entries()){let o=i.createOscillator(),c=i.createGain();o.frequency.value=n*a,c.gain.setValueAtTime(t/(r+1),e),c.gain.exponentialRampToValueAtTime(1e-4,e+1.6-r*.2),o.connect(c),this.bus(c,1,e),o.start(e),o.stop(e+1.7),o.onended=()=>{o.disconnect(),c.disconnect()}}}air(e,t=.25,n=.08,i=1600){let r=this.context,a=r.createBuffer(1,r.sampleRate*t,r.sampleRate),o=a.getChannelData(0);for(let h=0;h<o.length;h++)o[h]=(Math.random()*2-1)*Math.pow(1-h/o.length,1.7);let c=r.createBufferSource();c.buffer=a;let l=r.createBiquadFilter();l.type="bandpass",l.frequency.setValueAtTime(i,e),l.frequency.exponentialRampToValueAtTime(Math.max(100,i*.3),e+t),l.Q.value=.7,c.connect(l),this.bus(l,n,e),c.start(e),c.onended=()=>{c.disconnect(),l.disconnect()}}drum(e,t=.18){let n=this.context,i=n.createOscillator(),r=n.createGain();i.frequency.setValueAtTime(125,e),i.frequency.exponentialRampToValueAtTime(45,e+.19),r.gain.setValueAtTime(t,e),r.gain.exponentialRampToValueAtTime(1e-4,e+.35),i.connect(r),this.bus(r,1,e),i.start(e),i.stop(e+.36),i.onended=()=>{i.disconnect(),r.disconnect()}}phrase(e,t,n=!0){let i=MM[this.scene],r=60/(n?i.bpm:i.bpm*.73)/2,a=i.notes[e%8];return this.pluck(a,t,n?.095:.075,e%2?.5:-.5,1.7),e%2===0&&this.pluck(i.notes[(e+3)%8]-12,t+r*.5,.065,e%2?-.65:.65,1.8),e%8===0&&(this.strings([i.root-12,i.root,i.root+7,i.root+12],t,Math.min(3.6,r*9),n?.026:.02),this.flute(a+12,t+.09,Math.min(2.4,r*5),.05)),e%4===0&&(this.pluck(i.root-12,t,.15,-.15,2.2),n&&this.drum(t,this.scene===3?.23:.15)),n&&(e%8===6||this.scene===3&&e%2===1)&&(this.drum(t,.075),this.air(t,.1,.04,1900)),e%16===0&&this.gong(t,this.scene===3?.075:.04,i.root===48?65.4:98),this.scene===1&&e%8===5&&(this.air(t,.9,.08,1400),this.flute(i.notes[(e+2)%8]+12,t+.1,.7,.035)),this.scene===2&&(e%3===0&&this.waterDrop(t,.08,Math.sin(e)*.75),e%8===2&&this.air(t,1.1,.055,2400)),this.scene===3&&e%16===12&&(this.air(t,1.8,.12,220),this.drum(t+.2,.16)),r}schedule(){if(!this.context||!this.enabled||this.context.state!=="running"||["silent","outcome"].includes(this.mode))return;let e=this.context;for(this.nextBeat<e.currentTime-.2&&(this.nextBeat=e.currentTime+.05);this.nextBeat<e.currentTime+.25;)this.nextBeat+=this.phrase(this.step++%32,this.nextBeat,this.mode==="combat")}event(e){if(!this.context||!this.enabled||this.hidden)return;let t=this.context.currentTime+.008;e==="sword"?([81,86,93,98].forEach((n,i)=>this.pluck(n,t+i*.026,.15,(i-1.5)*.35,.9)),this.air(t,.12,.13,4200),this.air(t+.12,.25,.1,2100),this.gong(t+.17,.035,330),this.drum(t+.19,.07)):e==="guard"?(this.air(t,.35,.11,700),this.gong(t+.04,.13,146.83),[62,69,74,81].forEach((n,i)=>this.pluck(n,t+.06+i*.045,.14,(i-1.5)*.3,1.6)),this.strings([50,57,62],t+.08,1.2,.035)):e==="thunder"?([62,69,74,81,86].forEach((n,i)=>this.pluck(n,t+i*.025,.14,(i-2)*.2)),this.drum(t+.06,.32),this.air(t+.08,.65,.22,850),this.gong(t+.08,.14,73.4),this.air(t+.02,.1,.17,5e3),this.drum(t+.27,.21),this.air(t+.32,1.2,.15,220),this.flute(86,t+.38,.6,.045)):e==="parry"?(this.gong(t,.15,220),[86,93,98].forEach((n,i)=>this.pluck(n,t+i*.035,.2))):e==="enemy-killed"?(this.drum(t,.24),this.air(t,.12,.19,4e3),this.air(t+.08,.7,.14,750),[74,81,86,93].forEach((n,i)=>this.pluck(n,t+.07+i*.04,.1,(i-1.5)*.4,.8)),this.gong(t+.09,.065,196)):e==="enemy-hit"?(this.air(t,.09,.055,2200),this.pluck(62,t,.07,0,.25)):e==="enemy-dodge"||e==="dash"||e==="evade"?(this.air(t,.28,.12,2500),this.flute(86,t,.27,.045)):e==="hit"?(this.drum(t,.25),this.air(t,.25,.16,420)):e==="block"?(this.gong(t,.08,180),this.air(t,.13,.09,1600)):e==="enemy-cast"?(this.pluck(57,t,.13),this.air(t,.3,.09,1200)):e==="expose"||e==="armor-break"||e==="interrupt"?(this.gong(t,.12,220),[81,86,93].forEach((n,i)=>this.pluck(n,t+i*.045,.13))):e==="resist"?this.pluck(50,t,.05,0,.2):e==="hazard-warning"?(this.gong(t,.08,82.4),this.flute(57,t,.65,.07)):e==="hazard-strike"?(this.drum(t,.3),this.air(t,.6,.19,700)):e==="warning"?this.flute(57,t,.55,.07):e==="spawn"?(this.air(t,.55,.12,600),this.pluck(50,t,.1)):e==="travel"||e==="stage"||e==="seal"?(this.gong(t,.14,110),this.flute(81,t,.9,.07)):e==="finish"?([62,69,74,81,86,93].forEach((n,i)=>this.pluck(n,t+i*.11,.17,(i-2)*.15,2)),this.gong(t,.2,146.8)):e==="defeat"?(this.gong(t,.15,55),this.flute(62,t,1.5,.07)):e==="story"?(this.gong(t,.11,73.4),this.flute(74,t+.2,1.6,.05)):e==="empty"&&this.pluck(50,t,.08,0,.3)}setEndingMix(e,t){if(!this.context)return;let n=e?t?"done":"playing":"off";if(this.endingMix===n)return;this.endingMix=n;let i=this.context.currentTime;if(this.regularBus.gain.setTargetAtTime(e?0:1,i,.08),n==="playing"){let r=this.finaleBus;r.gain.setTargetAtTime(0,i,.03),setTimeout(()=>r.disconnect(),4e3),this.finaleBus=this.context.createGain(),this.finaleBus.connect(this.master),this.finaleBus.connect(this.space)}else this.finaleBus.gain.setTargetAtTime(0,i,.15)}endingCue(e){if(!this.context||!this.enabled||this.hidden||this.mode==="silent")return;let t=this.context.currentTime+.015;this.cinematicVoice=!0;try{e==="heartbeat"&&(this.drum(t,.19),this.drum(t+.25,.1)),e==="fracture"&&(this.air(t,1.3,.08,2600),[62,69,74,81,86].forEach((n,i)=>this.pluck(n,t+i*.28,.1,(i-2)*.3,1.7)),this.strings([38,50,57],t,2.2,.022)),e==="skybreak"&&(this.drum(t,.34),this.drum(t+.15,.22),this.gong(t,.22,65.4),this.air(t,.15,.23,3800),this.air(t+.07,2,.22,400),this.strings([38,50,57,62,69],t,3.5,.04),[62,69,74,81,86,93].forEach((n,i)=>this.pluck(n,t+.1+i*.09,.17,(i-2.5)*.3,2)),this.flute(86,t+.4,2.2,.075)),e==="soar"&&(this.strings([50,57,62,74],t,3.2,.035),[81,86,93].forEach((n,i)=>this.flute(n,t+i*.65,1.4,.065)),this.air(t,2,.055,1700)),e==="beacon"&&(this.gong(t,.1,293.6),this.pluck(98,t+.12,.16,0,2.4)),e==="heavens"&&(this.drum(t,.17),this.gong(t,.16,146.8),[74,81,86].forEach((n,i)=>this.pluck(n,t+i*.2,.15,(i-1)*.3,2.3)),this.strings([50,57,62,74],t,2.5,.035),this.flute(86,t+.3,1.8,.065))}finally{this.cinematicVoice=!1}}dispose(){clearInterval(this.timer);for(let e of this.ambient)e.source.stop(),e.source.disconnect(),e.filter.disconnect(),e.gain.disconnect();this.ambient=[],this.context?.close()}};var se=s=>document.getElementById(s),Tn=new Set,on=new Bc,Je,Zn,ro=!1,Wr=0,Ws=1/0,ao=0,kc=!0,so=null,_m=0,rd=0,ad=performance.now();function Hc(s,e="",t=1.5){se("cue").textContent=s,se("cue-small").textContent=e,ao=Wr+t}function hd(){on.unlock().catch(()=>{})}document.addEventListener("visibilitychange",()=>on.setHidden(document.hidden));on.setHidden(document.hidden);var Ve=new Dc(s=>{if(!ro)return;Je.effect(s),s.type!=="finish"&&on.event(s.type);let e={sword:["\u9053\u6307\u5251","\u98DE\u5251\u51FA\u9798"],thunder:["\u4E94\u96F7\u8BC0","\u7B26\u52A8\u96F7\u843D"],guard:["\u7834\u90AA\u5370","\u7ED3\u5370\u62A4\u8EAB"],parry:["\u5B8C\u7F8E\u53CD\u5236","\u5996\u6C14\u9006\u8F6C"],block:["\u62A4\u8EAB\u6210\u529F","\u5FA1\u5370\u627F\u4F24"],empty:["\u7075\u529B\u4E0D\u8DB3","\u98DE\u5251\u4E0D\u8017\u7075\u529B"],hit:["\u5996\u6C14\u4FB5\u4F53","E \u62A4\u8EAB \xB7 \u7A7A\u683C\u95EA\u8EAB"],evade:["\u95EA\u8EAB\u907F\u52AB",""],spawn:["\u5996\u5F71\u4E4D\u73B0","\u7559\u610F\u4FA7\u7FFC \xB7 Tab \u5207\u6362\u76EE\u6807"],travel:[s.area===1?"\u591C\u9B54\u5DF2\u9664":s.area===2?"\u5996\u7FFC\u5DF2\u788E":"\u6B64\u5883\u5DF2\u7834",s.area===1?"\u957F\u591C\u7834\u6653 \xB7 \u7A7F\u8FC7\u5C71\u95E8\uFF0C\u8E0F\u5165\u60AC\u6865":s.area===2?"\u8E0F\u8FC7\u60AC\u6865 \xB7 \u7A7F\u4EAD\u5165\u4E91 \xB7 \u843D\u5411\u955C\u6E56":$t[s.area]?.name||"\u524D\u5F80\u4E0B\u4E00\u5883"],expose:["\u955C\u969C\u5DF2\u7834","\u8D81\u6B64\u523B\u8FDB\u653B \xB7 \u7834\u90AA\u5370\u53EF\u518D\u7834\u955C\u969C"],"armor-break":["\u96F7\u7532\u5D29\u88C2","\u77F3\u5080\u5DF2\u5931\u53BB\u62A4\u7532"],interrupt:["\u5996\u7FFC\u5931\u8861","\u8FDE\u5251\u622A\u65AD\u4E86\u5B83\u7684\u6251\u51FB"],resist:["\u653B\u52BF\u53D7\u963B",s.reason==="mirror"?"\u5148\u7ED3\u7834\u90AA\u5370\uFF0C\u7834\u9664\u955C\u969C":"\u7528\u4E94\u96F7\u8BC0\u51FB\u788E\u96F7\u7532"],"hazard-warning":["\u811A\u4E0B\u6709\u96F7\uFF01","\u79FB\u51FA\u96F7\u5708\uFF0C\u6216\u4E34\u8EAB\u65F6\u62A4\u8EAB / \u95EA\u8EAB"],"enemy-dodge":["\u63A0\u5F71\u95EA\u907F","\u8BD5\u8BD5\u4E94\u96F7\u8BC0\u7684\u8303\u56F4\u96F7\u51FB"]};e[s.type]&&Hc(...e[s.type],s.type==="travel"?s.duration:.75),s.type==="hit"&&(se("damage-flash").style.opacity=.6,setTimeout(()=>se("damage-flash").style.opacity=0,160)),s.type==="finish"&&(Ws=1/0,se("hud").hidden=!0,ao=0,Tn.clear(),se("outcome-fx").hidden=!0,oo(!0)),s.type==="defeat"&&(Ws=Wr+2.4,se("hud").hidden=!0,se("outcome-fx").hidden=!1,se("outcome-fx").dataset.state="defeat",se("outcome-word").textContent="\u8BD5\u70BC\u5931\u8D25",se("outcome-line").textContent="\u795E\u9501\u53CD\u566C \xB7 \u6C14\u8840\u8017\u5C3D"),window.dispatchEvent(new CustomEvent("tianjie:feedback",{detail:{version:3,type:s.type,simulated:!0,color:fi[s.type]?.color||(s.type==="hit"?"#b54435":"#82e6c5")}}))});function ym(s,e="keyboard",t=1){if(Zn?.active)return so=Zn.input(s,e,t),so;let n=ro?Ve.rejection(s,t):{code:"loading",message:"\u6E38\u620F\u6B63\u5728\u52A0\u8F7D\uFF0C\u8BF7\u7A0D\u5019"};return so=n?{accepted:!1,...n}:{accepted:Ve.act(s,e,t),code:"accepted",message:"\u5DF2\u51FA\u62DB"},n&&n.code!=="travel"&&["gesture-adapter","touch"].includes(e)&&Hc(n.message,"\u653E\u677E\u540E\u518D\u505A\u4E00\u6B21",1.4),so}var ud=(s,e="keyboard",t=1)=>ym(s,e,t).accepted;function dd(){se("pause").textContent=Ve.paused?"\u7EE7\u7EED \u25B6":"\u6682\u505C \u2161",se("pause").setAttribute("aria-label",Ve.paused?"\u7EE7\u7EED":"\u6682\u505C")}function oo(s){se("ascension").hidden=!s,document.body.dataset.ending=String(s),document.body.style.setProperty("--ending-dark","0"),document.body.style.setProperty("--ending-logo","0"),se("ending-pause").textContent="\u6682\u505C \xB7 P"}function vm(){Ve.phase!=="victory"||!Je.ending.clock.active||Je.ending.clock.frame.done||(Je.ending.skip(),Ve.paused=!1)}function Wc(s){oo(!1),Ve.reset(),se("outcome-fx").hidden=!0,Ws=1/0,ao=0,Tn.clear(),se("advance").textContent="\u81EA\u52A8\u524D\u8FDB \u5F00",se("advance").setAttribute("aria-pressed","true"),se("result").hidden=!0,se("intro").hidden=s,se("hud").hidden=!s,s&&(hd(),Ve.start(),Hc("\u5931\u5E8F\u5C71\u95E8","Q \u98DE\u5251 \xB7 E \u62A4\u8EAB \xB7 R \u96F7\u7B26 \xB7 Tab \u6362\u654C",3)),dd()}function Xc(){!["combat","travel"].includes(Ve.phase)&&!(Ve.phase==="victory"&&Je.ending.clock.active&&!Je.ending.clock.frame.done)||(Ve.paused=!Ve.paused,Tn.clear(),dd(),se("ending-pause").textContent=Ve.paused?"\u7EE7\u7EED \xB7 P":"\u6682\u505C \xB7 P",Hc(Ve.paused?"\u6682\u6B47\u7247\u523B":"\u91CD\u8FD4\u8BF8\u5929",Ve.paused?"\u6309 P \u7EE7\u7EED":"",Ve.paused?999:1))}Zn=xm({preview:(s,e=!1)=>{Je&&(Je.previewPose=s,e&&(Je.effect({type:s}),on.event(s)))},startCombat:()=>Wc(!0),onOpen:()=>{oo(!1),hd(),on.event("story"),Ve.reset(),se("outcome-fx").hidden=!0,Ws=1/0,ao=0,Tn.clear(),se("intro").hidden=!0,se("hud").hidden=!0,se("result").hidden=!0},onClose:()=>{se("intro").hidden=!1,se("begin").focus()}});se("begin").onclick=()=>Zn.open();se("quickstart").onclick=()=>Wc(!0);se("replay-onboarding").onclick=()=>{se("guide").close(),Zn.open()};se("retry").onclick=()=>Wc(!0);se("return").onclick=()=>Wc(!1);se("pause").onclick=Xc;se("ending-pause").onclick=Xc;se("ending-skip").onclick=vm;se("ending-replay").onclick=()=>{Ve.phase==="victory"&&(Ve.paused=!1,Je.ending.start(),se("result").hidden=!0,oo(!0))};var Mm=!1;se("help").onclick=()=>{Mm=Ve.paused,Ve.paused=!0,Tn.clear(),se("guide").showModal()};se("close-help").onclick=()=>se("guide").close();se("guide").addEventListener("close",()=>{Ve.paused=Zn.active?!1:Mm,dd()});for(let[s,e,t,n]of[["testmode","testMode","tianjie-test","\u6D4B\u8BD5"],["godmode","godMode","tianjie-god","\u65E0\u654C"]]){let i=a=>{Ve[e]=a,se(s).textContent=`${n} ${a?"\u5F00":"\u5173"}`,se(s).setAttribute("aria-pressed",String(a));try{localStorage.setItem(t,a?"1":"0")}catch{}},r=!0;try{r=localStorage.getItem(t)!=="0"}catch{}i(r),se(s).onclick=()=>i(!Ve[e])}se("sound").onclick=()=>{hd(),on.setEnabled(!on.enabled),se("sound").textContent=`\u97F3\u6548 ${on.enabled?"\u5F00":"\u5173"}`,se("sound").setAttribute("aria-label",on.enabled?"\u5173\u95ED\u97F3\u6548":"\u5F00\u542F\u97F3\u6548")};se("quality").onclick=()=>{kc=!kc,Je?.quality(kc),se("quality").textContent=`\u753B\u8D28 ${kc?"\u9AD8":"\u6D41\u7545"}`};se("advance").onclick=()=>{Ve.autoAdvance=!Ve.autoAdvance,se("advance").textContent=Ve.autoAdvance?"\u81EA\u52A8\u524D\u8FDB \u5F00":"\u81EA\u52A8\u524D\u8FDB \u5173",se("advance").setAttribute("aria-pressed",String(Ve.autoAdvance))};se("fullscreen").onclick=()=>{(document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen())?.catch(()=>{})};se("export").onclick=()=>{let s=URL.createObjectURL(new Blob([JSON.stringify({version:3,kind:"local-gameplay",rawEMG:!1,snapshot:Ve.snapshot(),events:Ve.events},null,2)],{type:"application/json"})),e=document.createElement("a");e.href=s,e.download="zhangtian-session.json",e.click(),setTimeout(()=>URL.revokeObjectURL(s),1e3),se("export-note").textContent="\u5DF2\u5BFC\u51FA\uFF0C\u4E0D\u542B\u808C\u7535\u4FE1\u53F7\u3002"};document.querySelectorAll("[data-action]").forEach(s=>s.onclick=()=>ud(s.dataset.action,"touch"));document.querySelectorAll("[data-move]").forEach(s=>{let e={forward:"KeyW",back:"KeyS",left:"KeyA",right:"KeyD"}[s.dataset.move];s.onpointerdown=t=>{Tn.add(e),s.setPointerCapture(t.pointerId)},s.onpointerup=s.onpointercancel=()=>Tn.delete(e)});window.addEventListener("keydown",s=>{if(s.code==="Escape"&&!se("guide").open){vm();return}if(se("guide").open||s.target.matches("input,textarea,select,summary"))return;if(s.code==="Tab"){!Zn.active&&Ve.phase==="combat"&&(s.preventDefault(),Ve.cycleTarget());return}if(["Space","KeyQ","KeyE","KeyR","KeyW","KeyA","KeyS","KeyD","KeyP"].includes(s.code)&&s.preventDefault(),Tn.add(s.code),s.repeat)return;let e={KeyQ:"sword",KeyE:"guard",KeyR:"thunder",Space:"dash"}[s.code];e&&ud(e),s.code==="KeyP"&&!Zn.active&&Xc()});window.addEventListener("keyup",s=>Tn.delete(s.code));window.addEventListener("blur",()=>{Tn.clear(),(["combat","travel"].includes(Ve.phase)||Ve.phase==="victory"&&!Je.ending.clock.frame.done)&&!Ve.paused&&Xc()});var Xs=se("scene");Xs.oncontextmenu=s=>s.preventDefault();var ld=0,cd=0;Xs.onpointerdown=s=>{ro&&(s.button===2||s.pointerType==="touch"?(Je.dragging=!0,ld=s.clientX,cd=s.clientY,Xs.setPointerCapture(s.pointerId)):ud("sword","mouse"))};Xs.onpointermove=s=>{Je?.dragging&&(Je.yaw=Math.max(-2,Math.min(2,Je.yaw+(s.clientX-ld)*.004)),Je.pitch=Math.max(-.7,Math.min(.7,Je.pitch-(s.clientY-cd)*.004)),ld=s.clientX,cd=s.clientY)};Xs.onpointerup=Xs.onpointercancel=()=>{Je&&(Je.dragging=!1)};function Sm(s){return ym(["sword","guard","thunder"].includes(s?.gesture)?s.gesture:"invalid","gesture-adapter",s?.confidence??NaN)}var bm=s=>Sm(s).accepted,zc={state:"off",text:"\u672A\u6536\u5230\u8BC6\u522B\u9875\u72B6\u6001 \xB7 \u8BF7\u4FDD\u6301\u8BC6\u522B\u9875\u5F00\u542F",pose:"",acc:null},Vc=zc,Tm=-1/0,Gc=null;function wm(s){se("device-state").textContent="\u25CF "+s.text,se("device-state").dataset.state=s.state;let e=se("device-panel"),t=(s.state==="live"||s.state==="paused")&&!!s.lanes;e.hidden=!t,t&&(se("device-lanes").innerHTML=s.lanes.map((n,i)=>`<i data-lane="${n}" title="\u7B2C ${i+1} \u8DEF"></i>`).join(""),se("device-signal").textContent=s.signal,se("device-signal").dataset.bad=String(s.lanes.includes("bad")||s.state==="paused"),se("device-rec").textContent=s.rec||"\u2014")}function SM(s){let e=mm(s);return e?((e.state!=="live"||Vc.state!=="live")&&(Gc=null),Vc=e,Tm=performance.now(),e.state==="live"&&e.acc?(Gc||=e.acc,Je&&(Je.bandTilt=gm(Gc,e.acc))):Je&&(Je.bandTilt={pitch:0,roll:0}),Je&&(Je.bandPose=e.state==="live"?e.pose:""),wm(e),Zn.band(e),!0):!1}function bM(){Vc!==zc&&performance.now()-Tm>1500&&(Vc=zc,Gc=null,Je&&(Je.bandPose="",Je.bandTilt={pitch:0,roll:0}),wm(zc))}window.TianjieGame={input:bm,inputResult:Sm,band:SM,snapshot:()=>Ve.snapshot(),onboarding:()=>Zn.snapshot(),diagnostics:()=>({ready:ro,lastInput:so,fps:_m,audio:{enabled:on.enabled,state:on.context?.state||"locked",scene:on.scene},...Je?.diagnostics()})};window.addEventListener("tianjie:gesture",s=>bm(s.detail));var od=new Map;function TM(s){let e=Je.actors?.project(Je.camera,innerWidth,innerHeight)||[],t=new Map(e.map(n=>[n.id,n]));for(let n of s.enemies){let i=od.get(n.id);i||(i=document.createElement("button"),i.className="enemy-tag",i.innerHTML="<span></span><i><b></b></i>",i.onclick=()=>Ve.select(n.id),se("enemy-labels").append(i),od.set(n.id,i));let r=t.get(n.id);i.hidden=!r||!n.alive||!n.visible||s.phase!=="combat",r&&(i.style.transform=`translate(${r.x}px,${r.y}px) translate(-50%,-100%)`,i.dataset.target=String(n.id===s.targetId),i.dataset.attack=String(!!n.incoming),i.querySelector("span").textContent=n.name+(n.incoming?" \xB7 \u84C4\u52BF":""),i.querySelector("b").style.width=n.hp/n.maxHp*100+"%")}for(let[n,i]of od)s.enemies.some(r=>r.id===n)||(i.hidden=!0)}function wM(){let s=Ve.snapshot();on.setScene(s.phase==="travel"&&s.area===1&&(Je.journeyProgress||0)>.73?2:s.area),on.setMode(s.paused?"silent":["defeat","victory"].includes(s.phase)?"outcome":s.phase==="combat"?"combat":"explore");let e=Je.ending,t=e.clock.frame,n=Ve.phase==="victory"&&e.clock.active;if(on.setEndingMix(n,t.done),n){if(document.body.style.setProperty("--ending-dark",String(t.darken)),document.body.style.setProperty("--ending-logo",String(t.title)),se("ending-flash").style.opacity=String(t.flash),se("ending-caption").style.opacity=String(t.suspense),se("ending-chapter").textContent=t.chapter,se("ending-chapter").style.opacity=t.time<10.7?"1":"0",se("ending-skip").hidden=t.done,!Ve.paused)for(let i of e.clock.takeCues())on.endingCue(i);t.done&&se("result").hidden&&(Ws=Wr,oo(!1),document.body.dataset.ending="complete",document.body.style.setProperty("--ending-dark","1"),document.body.style.setProperty("--ending-logo","1"))}se("hp-value").textContent=`${Math.ceil(s.hp)}/100`,se("qi-value").textContent=`${Math.floor(s.qi)}/100`,se("hp-fill").style.width=s.hp+"%",se("qi-fill").style.width=s.qi+"%",se("enemy-hp").style.width=(s.target?s.target.hp/s.target.maxHp:0)*100+"%",se("enemy-title").textContent=s.target?.name||"\u5996\u5F71\u5C06\u81F3",se("boss-sub").textContent=`${s.areaName} \xB7 ${s.kills}/${s.totalEnemies} \u9547\u4F0F`,se("quest").textContent=s.phase==="travel"?`\u6B64\u5883\u5DF2\u7834 \xB7 \u524D\u5F80${$t[s.area+1]?.name||"\u4E0B\u4E00\u5883"}`:$t[s.area].subtitle,se("combo").textContent=s.combo>1?`COMBO ${s.combo}`:"",se("chapter-clear").hidden=!(s.phase==="travel"&&s.area===0&&!s.paused),document.body.dataset.daylight=String((Je.daylight||0)>.5),Wr>ao&&(se("cue-small").textContent=s.incoming?s.incoming.launched?"\u653B\u51FB\u4E34\u8EAB \xB7 E \u62A4\u8EAB / \u7A7A\u683C\u95EA\u8EAB":"\u5996\u6C14\u84C4\u52BF \xB7 \u7559\u610F\u7EA2\u8272\u76EE\u6807":"",se("cue").textContent=s.incoming?s.incoming.launched?"\u7ED3\u5370\u62A4\u8EAB":"\u4FA7\u7FFC\u6765\u88AD":""),document.querySelectorAll("[data-action]").forEach(i=>{i.classList.toggle("active",Je.handMode===i.dataset.action&&Je.handUntil>Je.time);let r=i.dataset.action==="sword"?.42:i.dataset.action==="guard"?1.45:fi[i.dataset.action].cooldown,a=Math.max(0,(s.cooldowns[i.dataset.action]||0)-s.time);i.querySelector("i").style.transform=`scaleX(${a/r})`,i.disabled=s.paused||s.phase==="travel"||!Ve.testMode&&a>0||!Ve.testMode&&s.phase==="combat"&&s.qi<fi[i.dataset.action].cost}),TM(s),s.phase==="travel"&&s.area>1?se("scene-curtain").style.opacity=String(Math.sin(Math.min(1,(s.time-(Ve.travelUntil-Ve.travelDuration))/Ve.travelDuration)*Math.PI)*.92):se("scene-curtain").style.opacity="0",Wr>=Ws&&(Ws=1/0,se("hud").hidden=!0,se("result").hidden=!1,se("result-title").textContent=s.phase==="victory"?"\u8BF8\u5929\u91CD\u660E":Ve.outcome,se("ending-replay").hidden=s.phase!=="victory",se("outcome-fx").hidden=!0,se("result").dataset.state=s.phase,se("result").setAttribute("aria-label",s.phase==="victory"?"\u8BD5\u70BC\u6210\u529F":"\u8BD5\u70BC\u5931\u8D25"),se("result-kicker").textContent=s.phase==="victory"?"\u7EC8\u7AE0 \xB7 \u8BF8\u5929\u91CD\u660E":`${s.areaName} \xB7 \u6C14\u8840\u8017\u5C3D`,se("result-desc").textContent=s.phase==="victory"?"\u957F\u591C\u5DF2\u5C3D\u3002\u4F60\u7684\u6545\u4E8B\uFF0C\u624D\u521A\u521A\u5F00\u59CB\u3002":"\u4F60\u5012\u4E0B\u4E86\uFF0C\u638C\u4E2D\u7684\u795E\u6027\u5374\u4ECD\u5728\u82CF\u9192\u3002\u770B\u51C6\u5996\u6C14\u4E34\u8EAB\uFF0C\u4EE5\u7834\u90AA\u5370\u62A4\u4F4F\u81EA\u5DF1\uFF0C\u518D\u95EF\u4E00\u6B21\u3002",se("result-stats").textContent=`\u7528\u65F6 ${s.time.toFixed(1)} \u79D2 \xB7 \u51FB\u8D25 ${s.kills} \u53EA \xB7 \u6700\u9AD8 ${s.bestCombo} \u8FDE\u51FB \xB7 \u6210\u529F\u683C\u6321 ${s.parries} \u6B21`)}(async()=>{try{let e=function(t){requestAnimationFrame(e);let n=Math.min(.05,(t-s)/1e3);s=t,rd++,t-ad>=1e3&&(_m=Math.round(rd*1e3/(t-ad)),rd=0,ad=t),Ve.paused||(Wr+=n),Je.move.set(Number(Tn.has("KeyD"))-Number(Tn.has("KeyA")),0,Number(Tn.has("KeyS"))-Number(Tn.has("KeyW"))),Je.move.lengthSq()>1&&Je.move.normalize(),bM(),Zn.active&&Zn.tick(document.hidden?0:n),Ve.setPlayer(Je.position),Ve.update(n),Je.update(Ve.paused?0:n,Ve.snapshot()),wM()};Je=new Nc(Xs,t=>{se("load-text").textContent=typeof t=="string"?t:"\u6B63\u5728\u6784\u7B51\u9053\u573A\u2026"}),await Je.init(),ro=!0,se("loading").hidden=!0,se("intro").hidden=!1;let s=performance.now();requestAnimationFrame(e)}catch(s){console.error(s),se("loading").hidden=!0,se("fatal").hidden=!1,se("fatal-message").textContent=s.message}})();
/*! Bundled license information:

three/build/three.core.js:
three/build/three.module.js:
  (**
   * @license
   * Copyright 2010-2026 Three.js Authors
   * SPDX-License-Identifier: MIT
   *)
*/
