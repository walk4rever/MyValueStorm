<template>
  <div class="research">
    <h1>Start New Research</h1>
    
    <div class="research-form">
      <div class="form-group">
        <label for="topic">Research Topic</label>
        <input 
          type="text" 
          id="topic" 
          v-model="topic" 
          placeholder="Enter a research topic"
          @keyup.enter="startResearch"
        >
      </div>
      
      <div class="form-group">
        <label for="depth">Research Depth</label>
        <select id="depth" v-model="depth">
          <option value="1">Basic (Faster)</option>
          <option value="2">Standard</option>
          <option value="3">Deep (More Comprehensive)</option>
        </select>
      </div>
      
      <div class="form-actions">
        <button 
          class="btn-primary" 
          @click="startResearch" 
          :disabled="!topic || loading"
        >
          {{ loading ? 'Starting Research...' : 'Start Research' }}
        </button>
      </div>
    </div>
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
    
    <div v-if="currentResearch" class="research-progress">
      <h2>Research in Progress</h2>
      <div class="progress-info">
        <p><strong>Topic:</strong> {{ currentResearch.topic }}</p>
        <p><strong>Status:</strong> {{ currentResearch.status }}</p>
        <p><strong>Started:</strong> {{ formatDate(currentResearch.startTime) }}</p>
      </div>
      
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: `${currentResearch.progress || 0}%` }"
        ></div>
      </div>
      <p class="progress-text">{{ currentResearch.progress || 0 }}% Complete</p>
      
      <div v-if="currentResearch.status === 'completed'" class="research-complete">
        <p>Research completed! View the results:</p>
        <router-link :to="`/results?id=${currentResearch.id}`" class="btn-secondary">
          View Results
        </router-link>
      </div>
    </div>
    
    <div class="previous-topics" v-if="researchTopics.length > 0">
      <h2>Previous Research Topics</h2>
      <ul class="topic-list">
        <li v-for="(topic, index) in researchTopics" :key="index" @click="selectTopic(topic)">
          {{ topic }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'ResearchView',
  data() {
    return {
      topic: '',
      depth: '2',
      loading: false,
      error: null,
      researchInterval: null
    }
  },
  computed: {
    ...mapGetters({
      researchTopics: 'getResearchTopics',
      currentResearch: 'getCurrentResearch',
      error: 'getError'
    })
  },
  methods: {
    async startResearch() {
      if (!this.topic) return;
      
      try {
        this.loading = true;
        this.error = null;
        
        await this.$store.dispatch('startResearch', {
          topic: this.topic,
          depth: parseInt(this.depth)
        });
        
        // Start polling for research progress
        this.startProgressPolling();
        
      } catch (error) {
        this.error = 'Failed to start research. Please try again.';
        console.error('Research error:', error);
      } finally {
        this.loading = false;
      }
    },
    selectTopic(topic) {
      this.topic = topic;
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleString();
    },
    startProgressPolling() {
      // Clear any existing interval
      if (this.researchInterval) {
        clearInterval(this.researchInterval);
      }
      
      // Poll for research progress every 3 seconds
      this.researchInterval = setInterval(async () => {
        if (this.currentResearch && this.currentResearch.status === 'completed') {
          clearInterval(this.researchInterval);
          return;
        }
        
        try {
          // Replace with your actual API endpoint to get research progress
          const response = await fetch(`/api/research/progress/${this.currentResearch.id}`);
          const data = await response.json();
          
          // Update the current research with progress information
          this.$store.commit('SET_CURRENT_RESEARCH', {
            ...this.currentResearch,
            ...data
          });
          
          if (data.status === 'completed') {
            clearInterval(this.researchInterval);
          }
        } catch (error) {
          console.error('Error fetching research progress:', error);
        }
      }, 3000);
    }
  },
  mounted() {
    this.$store.dispatch('fetchResearchTopics');
    
    // If there's an ongoing research, start polling for progress
    if (this.currentResearch && this.currentResearch.status !== 'completed') {
      this.startProgressPolling();
    }
  },
  beforeUnmount() {
    // Clear the interval when component is destroyed
    if (this.researchInterval) {
      clearInterval(this.researchInterval);
    }
  }
}
</script>

<style scoped>
.research {
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.research-form {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

input, select {
  width: 100%;
  padding: 0.8rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  background-color: #42b983;
  color: white;
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-primary:hover:not(:disabled) {
  background-color: #3aa876;
}

.btn-primary:disabled {
  background-color: #a8d5c2;
  cursor: not-allowed;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 2rem;
}

.research-progress {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.progress-info {
  margin-bottom: 1.5rem;
}

.progress-info p {
  margin-bottom: 0.5rem;
}

.progress-bar {
  height: 10px;
  background-color: #e9ecef;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background-color: #42b983;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: right;
  font-size: 0.9rem;
  color: #6c757d;
}

.research-complete {
  margin-top: 1.5rem;
  text-align: center;
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

.previous-topics {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.topic-list {
  list-style: none;
  padding: 0;
}

.topic-list li {
  padding: 0.8rem;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background-color 0.3s;
}

.topic-list li:last-child {
  border-bottom: none;
}

.topic-list li:hover {
  background-color: #f8f9fa;
}
</style>
