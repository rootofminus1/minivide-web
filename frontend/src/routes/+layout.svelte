<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { currentUser } from '$lib/stores.js';
    import { page } from '$app/state';

	// for spa behavior
	export const prerender = false;
	export const ssr = false;

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<nav>
    <a href="/" class="brand">MiniVide</a>

    <div class="nav-right">
        <span class="user-label">Dev user:</span>
        {#each currentUser.USERS as user}
            <button
                class="border border-s-2 border-amber-400 p-2"
                class:active={$currentUser === user}
                onclick={() => currentUser.switch(user)}
            >
                {user}
            </button>
        {/each}

        <a href="/editor" class="new-edit-btn">+ New Edit</a>
    </div>
</nav>

<main>
    {@render children()}    
</main>

