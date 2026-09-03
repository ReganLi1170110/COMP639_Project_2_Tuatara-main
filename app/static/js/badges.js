async function loadBadges(){
    try{
        const resp = await fetch('/api/user/badges', {credentials: 'same-origin'});
        if(!resp.ok) return;
        const data = await resp.json();
        window.badgeData = data;
        const evt = new CustomEvent('badgesLoaded', {detail: data});
        document.dispatchEvent(evt);
    }catch(e){console.error('Failed to load badges', e)}
}

document.addEventListener('DOMContentLoaded', () => {
    loadBadges();
});
