<template>
  <div class="home">
    <section class="hero">
      <div class="hero-content">
        <h1>Welcome to ValueStorm</h1>
        <p>An advanced research assistant powered by STORM technology</p>
        <router-link to="/research" class="btn-primary">Start Research</router-link>
      </div>
    </section>

    <section class="features">
      <h2>Features</h2>
      <div class="feature-grid">
        <div class="feature-card">
          <div class="feature-icon">🔍</div>
          <h3>Comprehensive Research</h3>
          <p>Conduct thorough research on any topic with our advanced STORM technology</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>Detailed Analysis</h3>
          <p>Get detailed analysis and insights from multiple sources</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <h3>Fast Results</h3>
          <p>Receive research results quickly and efficiently</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📝</div>
          <h3>Organized Output</h3>
          <p>View research results in a well-structured and organized format</p>
        </div>
      </div>
    </section>

    <section class="recent-research" v-if="recentResults.length > 0">
      <h2>Recent Research</h2>
      <div class="research-list">
        <div v-for="result in recentResults" :key="result.id" class="research-card">
          <h3>{{ result.topic }}</h3>
          <p>{{ result.summary }}</p>
          <router-link :to="'/results?id=' + result.id" class="btn-secondary">View Details</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'HomeView',
  computed: {
    ...mapGetters(['getResearchResults']),
    recentResults() {
      // Get the 3 most recent research results
      return this.getResearchResults.slice(0, 3);
    }
  },
  mounted() {
    this.$store.dispatch('fetchResearchResults');
  }
}
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.hero {
  background-color: #2c3e50;
  color: white;
  padding: 4rem 2rem;
  border-radius: 8px;
  text-align: center;
}

.hero h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.hero p {
  font-size: 1.2rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}

.btn-primary {
  display: inline-block;
  background-color: #42b983;
  color: white;
  padding: 0.8rem 1.5rem;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  transition: background-color 0.3s;
}

.btn-primary:hover {
  background-color: #3aa876;
}

.features h2, .recent-research h2 {
  text-align: center;
  margin-bottom: 2rem;
  font-size: 2rem;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}

.feature-card {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.research-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.research-card {
  background-color: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.research-card h3 {
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.research-card p {
  margin-bottom: 1rem;
  color: #666;
}

.btn-secondary {
  display: inline-block;
  background-color: transparent;
  color: #42b983;
  padding: 0.5rem 1rem;
  border: 1px solid #42b983;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background-color: #42b983;
  color: white;
}
</style>
