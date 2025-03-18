<template>
  <div class="results">
    <h1>Research Results</h1>
    
    <div v-if="loading" class="loading">
      <p>Loading research results...</p>
    </div>
    
    <div v-else-if="error" class="error-message">
      {{ error }}
    </div>
    
    <div v-else-if="selectedResult" class="result-detail">
      <div class="result-header">
        <h2>{{ selectedResult.topic }}</h2>
        <div class="result-meta">
          <span><strong>Completed:</strong> {{ formatDate(selectedResult.completedTime) }}</span>
          <span><strong>Research Depth:</strong> {{ getDepthLabel(selectedResult.depth) }}</span>
        </div>
      </div>
      
      <div class="result-content">
        <div class="result-summary">
          <h3>Summary</h3>
          <p>{{ selectedResult.summary }}</p>
        </div>
        
        <div class="result-sections">
          <div v-for="(section, index) in selectedResult.sections" :key="index" class="result-section">
            <h3>{{ section.title }}</h3>
            <div v-html="formatContent(section.content)"></div>
            
            <div v-if="section.sources && section.sources.length > 0" class="section-sources">
              <h4>Sources</h4>
              <ul>
                <li v-for="(source, sourceIndex) in section.sources" :key="sourceIndex">
                  <a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title }}</a>
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        <div class="result-references" v-if="selectedResult.references && selectedResult.references.length > 0">
          <h3>References</h3>
          <ul>
            <li v-for="(reference, index) in selectedResult.references" :key="index">
              <a :href="reference.url" target="_blank" rel="noopener noreferrer">{{ reference.title }}</a>
              <p v-if="reference.description">{{ reference.description }}</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
    
    <div v-else-if="researchResults.length > 0" class="results-list">
      <div v-for="result in researchResults" :key="result.id" class="result-card" @click="viewResult(result.id)">
        <h3>{{ result.topic }}</h3>
        <p class="result-date">{{ formatDate(result.completedTime) }}</p>
        <p class="result-summary">{{ truncate(result.summary, 150) }}</p>
        <button class="btn-secondary">View Details</button>
      </div>
    </div>
    
    <div v-else class="no-results">
      <p>No research results found.</p>
      <router-link to="/research" class="btn-primary">Start New Research</router-link>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'ResultsView',
  data() {
    return {
      selectedResult: null,
      selectedId: null
    }
  },
  computed: {
    ...mapGetters(['getResearchResults', 'isLoading', 'getError']),
    loading() {
      return this.isLoading;
    },
    error() {
      return this.getError;
    },
    researchResults() {
      return this.getResearchResults;
    }
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleString();
    },
    truncate(text, length) {
      if (!text) return '';
      return text.length > length ? text.substring(0, length) + '...' : text;
    },
    getDepthLabel(depth) {
      const depthMap = {
        1: 'Basic',
        2: 'Standard',
        3: 'Deep'
      };
      return depthMap[depth] || 'Standard';
    },
    formatContent(content) {
      // Simple formatting for content (could be enhanced with a markdown parser)
      if (!content) return '';
      
      // Replace newlines with <br> tags
      let formatted = content.replace(/\n/g, '<br>');
      
      // Bold text between ** markers
      formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      
      // Italic text between * markers
      formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
      
      return formatted;
    },
    async viewResult(id) {
      this.selectedId = id;
      
      try {
        // Replace with your actual API endpoint
        const response = await fetch(`/api/research/results/${id}`);
        const data = await response.json();
        this.selectedResult = data;
        
        // Update URL without reloading the page
        const url = new URL(window.location);
        url.searchParams.set('id', id);
        window.history.pushState({}, '', url);
        
      } catch (error) {
        console.error('Error fetching research result:', error);
        this.$store.commit('SET_ERROR', 'Failed to load research result');
      }
    }
  },
  async mounted() {
    await this.$store.dispatch('fetchResearchResults');
    
    // Check if there's an ID in the URL query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const resultId = urlParams.get('id');
    
    if (resultId) {
      this.viewResult(resultId);
    }
  }
}
</script>

<style scoped>
.results {
  max-width: 900px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.loading, .no-results {
  text-align: center;
  padding: 3rem 0;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 2rem;
}

.results-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
}

.result-card {
  background-color: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.result-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.result-card h3 {
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.result-date {
  font-size: 0.9rem;
  color: #6c757d;
  margin-bottom: 1rem;
}

.result-summary {
  margin-bottom: 1.5rem;
  color: #495057;
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
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #42b983;
  color: white;
}

.result-detail {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.result-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
}

.result-header h2 {
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.result-meta {
  display: flex;
  gap: 2rem;
  color: #6c757d;
  font-size: 0.9rem;
}

.result-summary {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.result-section {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
}

.result-section h3 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.section-sources {
  margin-top: 1rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #eee;
}

.section-sources h4 {
  margin-bottom: 0.5rem;
  font-size: 1rem;
  color: #6c757d;
}

.section-sources ul, .result-references ul {
  padding-left: 1.5rem;
}

.section-sources li, .result-references li {
  margin-bottom: 0.5rem;
}

.section-sources a, .result-references a {
  color: #0066cc;
  text-decoration: none;
}

.section-sources a:hover, .result-references a:hover {
  text-decoration: underline;
}

.result-references {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 2px solid #eee;
}

.result-references h3 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.result-references p {
  font-size: 0.9rem;
  color: #6c757d;
  margin-top: 0.25rem;
}
</style>
