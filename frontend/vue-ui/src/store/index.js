import { createStore } from 'vuex'
import axios from 'axios'

export default createStore({
  state: {
    researchTopics: [],
    currentResearch: null,
    researchResults: [],
    loading: false,
    error: null
  },
  getters: {
    getResearchTopics: state => state.researchTopics,
    getCurrentResearch: state => state.currentResearch,
    getResearchResults: state => state.researchResults,
    isLoading: state => state.loading,
    getError: state => state.error
  },
  mutations: {
    SET_RESEARCH_TOPICS(state, topics) {
      state.researchTopics = topics;
    },
    SET_CURRENT_RESEARCH(state, research) {
      state.currentResearch = research;
    },
    SET_RESEARCH_RESULTS(state, results) {
      state.researchResults = results;
    },
    SET_LOADING(state, isLoading) {
      state.loading = isLoading;
    },
    SET_ERROR(state, error) {
      state.error = error;
    }
  },
  actions: {
    async fetchResearchTopics({ commit }) {
      try {
        commit('SET_LOADING', true);
        // Replace with your actual API endpoint
        const response = await axios.get('/api/research/topics');
        commit('SET_RESEARCH_TOPICS', response.data);
        commit('SET_ERROR', null);
      } catch (error) {
        commit('SET_ERROR', 'Failed to fetch research topics');
        console.error('Error fetching research topics:', error);
      } finally {
        commit('SET_LOADING', false);
      }
    },
    async startResearch({ commit }, data) {
      try {
        commit('SET_LOADING', true);
        console.log('Starting research with data:', data);
        // Replace with your actual API endpoint
        const response = await axios.post('/api/research/start', data);
        console.log('Research started:', response.data);
        commit('SET_CURRENT_RESEARCH', response.data);
        commit('SET_ERROR', null);
        return response.data;
      } catch (error) {
        commit('SET_ERROR', 'Failed to start research');
        console.error('Error starting research:', error);
        throw error;
      } finally {
        commit('SET_LOADING', false);
      }
    },
    async fetchResearchResults({ commit }) {
      try {
        commit('SET_LOADING', true);
        // Replace with your actual API endpoint
        const response = await axios.get('/api/research/results');
        commit('SET_RESEARCH_RESULTS', response.data);
        commit('SET_ERROR', null);
      } catch (error) {
        commit('SET_ERROR', 'Failed to fetch research results');
        console.error('Error fetching research results:', error);
      } finally {
        commit('SET_LOADING', false);
      }
    }
  }
})
