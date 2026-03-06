--
-- PostgreSQL database dump
--

\restrict i1zIixLaxsHWawsCMcTvRhkoNw9yROQrFeBHcyCuxEoRmJvLN3arHLGtmyan06E

-- Dumped from database version 16.11 (Homebrew)
-- Dumped by pg_dump version 16.11 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alternatives; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alternatives (
    alternative_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: criteria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.criteria (
    criterion_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    direction text NOT NULL,
    scale_type text NOT NULL,
    unit text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT criteria_direction_check CHECK ((direction = ANY (ARRAY['benefit'::text, 'cost'::text]))),
    CONSTRAINT criteria_scale_type_check CHECK ((scale_type = ANY (ARRAY['ratio'::text, 'interval'::text, 'ordinal'::text, 'binary'::text])))
);


--
-- Name: criterion_weights; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.criterion_weights (
    preference_set_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    weight double precision NOT NULL,
    weight_type text DEFAULT 'normalized'::text NOT NULL,
    derived_from text DEFAULT 'direct'::text NOT NULL,
    CONSTRAINT criterion_weights_derived_from_check CHECK ((derived_from = ANY (ARRAY['direct'::text, 'ahp'::text, 'vft'::text, 'qfd'::text]))),
    CONSTRAINT criterion_weights_weight_check CHECK ((weight >= (0)::double precision)),
    CONSTRAINT criterion_weights_weight_type_check CHECK ((weight_type = ANY (ARRAY['raw'::text, 'normalized'::text])))
);


--
-- Name: decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.decisions (
    decision_id uuid DEFAULT gen_random_uuid() NOT NULL,
    title text NOT NULL,
    purpose text,
    status text DEFAULT 'draft'::text NOT NULL,
    owner_team text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT decisions_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'archived'::text])))
);


--
-- Name: measurements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.measurements (
    measurement_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    value_num double precision NOT NULL,
    source text,
    confidence double precision,
    note text,
    collected_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT measurements_confidence_check CHECK (((confidence IS NULL) OR ((confidence >= (0)::double precision) AND (confidence <= (1)::double precision))))
);


--
-- Name: preference_sets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.preference_sets (
    preference_set_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    type text NOT NULL,
    name text DEFAULT 'Default Weights'::text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text,
    note text,
    CONSTRAINT preference_sets_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'archived'::text]))),
    CONSTRAINT preference_sets_type_check CHECK ((type = ANY (ARRAY['direct'::text, 'ahp'::text, 'vft'::text, 'qfd'::text])))
);


--
-- Name: result_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.result_scores (
    run_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    score double precision NOT NULL,
    rank integer
);


--
-- Name: runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.runs (
    run_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    preference_set_id uuid NOT NULL,
    method text NOT NULL,
    engine_version text DEFAULT 'core=0.1.0'::text NOT NULL,
    executed_at timestamp with time zone DEFAULT now() NOT NULL,
    executed_by text,
    input_signature text,
    run_label text,
    CONSTRAINT runs_method_check CHECK ((method = ANY (ARRAY['topsis'::text, 'vft'::text])))
);


--
-- Name: scenario_validation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scenario_validation (
    scenario_id uuid NOT NULL,
    is_complete_matrix boolean NOT NULL,
    missing_cells_count integer DEFAULT 0 NOT NULL,
    computed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scenarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scenarios (
    scenario_id uuid DEFAULT gen_random_uuid() NOT NULL,
    decision_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text
);


--
-- Name: topsis_distances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topsis_distances (
    run_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    s_pos double precision NOT NULL,
    s_neg double precision NOT NULL,
    c_star double precision NOT NULL
);


--
-- Name: topsis_ideals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topsis_ideals (
    run_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    pos_ideal double precision NOT NULL,
    neg_ideal double precision NOT NULL
);


--
-- Name: topsis_normalized_values; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topsis_normalized_values (
    run_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    value double precision NOT NULL
);


--
-- Name: topsis_run_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topsis_run_config (
    run_id uuid NOT NULL,
    normalization text NOT NULL,
    distance text NOT NULL,
    CONSTRAINT topsis_run_config_distance_check CHECK ((distance = 'euclidean'::text)),
    CONSTRAINT topsis_run_config_normalization_check CHECK ((normalization = 'vector'::text))
);


--
-- Name: topsis_weighted_values; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topsis_weighted_values (
    run_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    value double precision NOT NULL
);


--
-- Name: value_function_points; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.value_function_points (
    value_function_id uuid NOT NULL,
    point_order integer NOT NULL,
    x double precision NOT NULL,
    y double precision NOT NULL,
    CONSTRAINT value_function_points_y_check CHECK (((y >= (0)::double precision) AND (y <= (1)::double precision)))
);


--
-- Name: value_functions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.value_functions (
    value_function_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    function_type text NOT NULL,
    output_min double precision DEFAULT 0.0 NOT NULL,
    output_max double precision DEFAULT 1.0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text,
    note text,
    CONSTRAINT value_functions_function_type_check CHECK ((function_type = ANY (ARRAY['piecewise_linear'::text, 'linear'::text])))
);


--
-- Name: vft_criterion_utilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vft_criterion_utilities (
    run_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    raw_value double precision NOT NULL,
    utility_value double precision NOT NULL
);


--
-- Name: vft_run_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vft_run_config (
    run_id uuid NOT NULL,
    output_min double precision DEFAULT 0.0 NOT NULL,
    output_max double precision DEFAULT 1.0 NOT NULL,
    missing_policy text DEFAULT 'reject'::text NOT NULL,
    CONSTRAINT vft_run_config_missing_policy_check CHECK ((missing_policy = 'reject'::text))
);


--
-- Name: vft_weighted_utilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vft_weighted_utilities (
    run_id uuid NOT NULL,
    alternative_id uuid NOT NULL,
    criterion_id uuid NOT NULL,
    weight double precision NOT NULL,
    weighted_utility double precision NOT NULL
);


--
-- Name: alternatives alternatives_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alternatives
    ADD CONSTRAINT alternatives_pkey PRIMARY KEY (alternative_id);


--
-- Name: alternatives alternatives_scenario_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alternatives
    ADD CONSTRAINT alternatives_scenario_id_name_key UNIQUE (scenario_id, name);


--
-- Name: criteria criteria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteria
    ADD CONSTRAINT criteria_pkey PRIMARY KEY (criterion_id);


--
-- Name: criteria criteria_scenario_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteria
    ADD CONSTRAINT criteria_scenario_id_name_key UNIQUE (scenario_id, name);


--
-- Name: criterion_weights criterion_weights_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criterion_weights
    ADD CONSTRAINT criterion_weights_pkey PRIMARY KEY (preference_set_id, criterion_id);


--
-- Name: decisions decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decisions
    ADD CONSTRAINT decisions_pkey PRIMARY KEY (decision_id);


--
-- Name: measurements measurements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.measurements
    ADD CONSTRAINT measurements_pkey PRIMARY KEY (measurement_id);


--
-- Name: measurements measurements_scenario_id_alternative_id_criterion_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.measurements
    ADD CONSTRAINT measurements_scenario_id_alternative_id_criterion_id_key UNIQUE (scenario_id, alternative_id, criterion_id);


--
-- Name: preference_sets preference_sets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preference_sets
    ADD CONSTRAINT preference_sets_pkey PRIMARY KEY (preference_set_id);


--
-- Name: preference_sets preference_sets_scenario_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preference_sets
    ADD CONSTRAINT preference_sets_scenario_id_name_key UNIQUE (scenario_id, name);


--
-- Name: result_scores result_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.result_scores
    ADD CONSTRAINT result_scores_pkey PRIMARY KEY (run_id, alternative_id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (run_id);


--
-- Name: scenario_validation scenario_validation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scenario_validation
    ADD CONSTRAINT scenario_validation_pkey PRIMARY KEY (scenario_id);


--
-- Name: scenarios scenarios_decision_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_decision_id_name_key UNIQUE (decision_id, name);


--
-- Name: scenarios scenarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_pkey PRIMARY KEY (scenario_id);


--
-- Name: topsis_distances topsis_distances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_distances
    ADD CONSTRAINT topsis_distances_pkey PRIMARY KEY (run_id, alternative_id);


--
-- Name: topsis_ideals topsis_ideals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_ideals
    ADD CONSTRAINT topsis_ideals_pkey PRIMARY KEY (run_id, criterion_id);


--
-- Name: topsis_normalized_values topsis_normalized_values_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_normalized_values
    ADD CONSTRAINT topsis_normalized_values_pkey PRIMARY KEY (run_id, alternative_id, criterion_id);


--
-- Name: topsis_run_config topsis_run_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_run_config
    ADD CONSTRAINT topsis_run_config_pkey PRIMARY KEY (run_id);


--
-- Name: topsis_weighted_values topsis_weighted_values_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_weighted_values
    ADD CONSTRAINT topsis_weighted_values_pkey PRIMARY KEY (run_id, alternative_id, criterion_id);


--
-- Name: value_function_points value_function_points_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_function_points
    ADD CONSTRAINT value_function_points_pkey PRIMARY KEY (value_function_id, point_order);


--
-- Name: value_function_points value_function_points_value_function_id_x_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_function_points
    ADD CONSTRAINT value_function_points_value_function_id_x_key UNIQUE (value_function_id, x);


--
-- Name: value_functions value_functions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_functions
    ADD CONSTRAINT value_functions_pkey PRIMARY KEY (value_function_id);


--
-- Name: value_functions value_functions_scenario_id_criterion_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_functions
    ADD CONSTRAINT value_functions_scenario_id_criterion_id_key UNIQUE (scenario_id, criterion_id);


--
-- Name: vft_criterion_utilities vft_criterion_utilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_criterion_utilities
    ADD CONSTRAINT vft_criterion_utilities_pkey PRIMARY KEY (run_id, alternative_id, criterion_id);


--
-- Name: vft_run_config vft_run_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_run_config
    ADD CONSTRAINT vft_run_config_pkey PRIMARY KEY (run_id);


--
-- Name: vft_weighted_utilities vft_weighted_utilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_weighted_utilities
    ADD CONSTRAINT vft_weighted_utilities_pkey PRIMARY KEY (run_id, alternative_id, criterion_id);


--
-- Name: idx_alternatives_scenario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_alternatives_scenario_id ON public.alternatives USING btree (scenario_id);


--
-- Name: idx_criteria_scenario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_criteria_scenario_id ON public.criteria USING btree (scenario_id);


--
-- Name: idx_criterion_weights_criterion_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_criterion_weights_criterion_id ON public.criterion_weights USING btree (criterion_id);


--
-- Name: idx_measurements_alt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_measurements_alt_id ON public.measurements USING btree (alternative_id);


--
-- Name: idx_measurements_crit_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_measurements_crit_id ON public.measurements USING btree (criterion_id);


--
-- Name: idx_measurements_scenario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_measurements_scenario_id ON public.measurements USING btree (scenario_id);


--
-- Name: idx_preference_sets_scenario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_preference_sets_scenario_id ON public.preference_sets USING btree (scenario_id);


--
-- Name: idx_result_scores_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_result_scores_run_id ON public.result_scores USING btree (run_id);


--
-- Name: idx_runs_scenario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_scenario_id ON public.runs USING btree (scenario_id);


--
-- Name: idx_runs_sig; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_sig ON public.runs USING btree (scenario_id, preference_set_id, method, input_signature);


--
-- Name: idx_scenarios_decision_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scenarios_decision_id ON public.scenarios USING btree (decision_id);


--
-- Name: idx_value_functions_scenario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_value_functions_scenario_id ON public.value_functions USING btree (scenario_id);


--
-- Name: alternatives alternatives_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alternatives
    ADD CONSTRAINT alternatives_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: criteria criteria_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteria
    ADD CONSTRAINT criteria_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: criterion_weights criterion_weights_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criterion_weights
    ADD CONSTRAINT criterion_weights_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: criterion_weights criterion_weights_preference_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criterion_weights
    ADD CONSTRAINT criterion_weights_preference_set_id_fkey FOREIGN KEY (preference_set_id) REFERENCES public.preference_sets(preference_set_id) ON DELETE CASCADE;


--
-- Name: measurements measurements_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.measurements
    ADD CONSTRAINT measurements_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: measurements measurements_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.measurements
    ADD CONSTRAINT measurements_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: measurements measurements_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.measurements
    ADD CONSTRAINT measurements_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: preference_sets preference_sets_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preference_sets
    ADD CONSTRAINT preference_sets_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: result_scores result_scores_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.result_scores
    ADD CONSTRAINT result_scores_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: result_scores result_scores_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.result_scores
    ADD CONSTRAINT result_scores_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: runs runs_preference_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_preference_set_id_fkey FOREIGN KEY (preference_set_id) REFERENCES public.preference_sets(preference_set_id) ON DELETE RESTRICT;


--
-- Name: runs runs_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: scenario_validation scenario_validation_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scenario_validation
    ADD CONSTRAINT scenario_validation_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: scenarios scenarios_decision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.decisions(decision_id) ON DELETE CASCADE;


--
-- Name: topsis_distances topsis_distances_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_distances
    ADD CONSTRAINT topsis_distances_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: topsis_distances topsis_distances_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_distances
    ADD CONSTRAINT topsis_distances_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: topsis_ideals topsis_ideals_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_ideals
    ADD CONSTRAINT topsis_ideals_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: topsis_ideals topsis_ideals_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_ideals
    ADD CONSTRAINT topsis_ideals_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: topsis_normalized_values topsis_normalized_values_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_normalized_values
    ADD CONSTRAINT topsis_normalized_values_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: topsis_normalized_values topsis_normalized_values_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_normalized_values
    ADD CONSTRAINT topsis_normalized_values_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: topsis_normalized_values topsis_normalized_values_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_normalized_values
    ADD CONSTRAINT topsis_normalized_values_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: topsis_run_config topsis_run_config_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_run_config
    ADD CONSTRAINT topsis_run_config_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: topsis_weighted_values topsis_weighted_values_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_weighted_values
    ADD CONSTRAINT topsis_weighted_values_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: topsis_weighted_values topsis_weighted_values_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_weighted_values
    ADD CONSTRAINT topsis_weighted_values_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: topsis_weighted_values topsis_weighted_values_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topsis_weighted_values
    ADD CONSTRAINT topsis_weighted_values_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: value_function_points value_function_points_value_function_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_function_points
    ADD CONSTRAINT value_function_points_value_function_id_fkey FOREIGN KEY (value_function_id) REFERENCES public.value_functions(value_function_id) ON DELETE CASCADE;


--
-- Name: value_functions value_functions_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_functions
    ADD CONSTRAINT value_functions_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: value_functions value_functions_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.value_functions
    ADD CONSTRAINT value_functions_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: vft_criterion_utilities vft_criterion_utilities_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_criterion_utilities
    ADD CONSTRAINT vft_criterion_utilities_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: vft_criterion_utilities vft_criterion_utilities_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_criterion_utilities
    ADD CONSTRAINT vft_criterion_utilities_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: vft_criterion_utilities vft_criterion_utilities_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_criterion_utilities
    ADD CONSTRAINT vft_criterion_utilities_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: vft_run_config vft_run_config_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_run_config
    ADD CONSTRAINT vft_run_config_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: vft_weighted_utilities vft_weighted_utilities_alternative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_weighted_utilities
    ADD CONSTRAINT vft_weighted_utilities_alternative_id_fkey FOREIGN KEY (alternative_id) REFERENCES public.alternatives(alternative_id) ON DELETE CASCADE;


--
-- Name: vft_weighted_utilities vft_weighted_utilities_criterion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_weighted_utilities
    ADD CONSTRAINT vft_weighted_utilities_criterion_id_fkey FOREIGN KEY (criterion_id) REFERENCES public.criteria(criterion_id) ON DELETE CASCADE;


--
-- Name: vft_weighted_utilities vft_weighted_utilities_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vft_weighted_utilities
    ADD CONSTRAINT vft_weighted_utilities_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict i1zIixLaxsHWawsCMcTvRhkoNw9yROQrFeBHcyCuxEoRmJvLN3arHLGtmyan06E

