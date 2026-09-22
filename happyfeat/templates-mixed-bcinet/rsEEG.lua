
function initialize(box)

	dofile(box:get_config("${Path_Data}") .. "/plugins/stimulation/lua-stimulator-stim-codes.lua")
	duration = box:get_setting(2)

end

function process(box)

	local t=0

	-- manages baseline

	box:send_stimulation(1, OVTK_StimulationId_ExperimentStart, t, 0)
	t = t + 5

	box:send_stimulation(1, OVTK_StimulationId_BaselineStart, t, 0)
	t = t + duration

	box:send_stimulation(1, OVTK_StimulationId_BaselineStop, t, 0)


	-- send end for completeness
	box:send_stimulation(1, OVTK_GDF_End_Of_Session, t, 0)
	t = t + 5
	
	-- used to cause the acquisition scenario to stop
	box:send_stimulation(1, OVTK_StimulationId_ExperimentStop, t, 0)

end
