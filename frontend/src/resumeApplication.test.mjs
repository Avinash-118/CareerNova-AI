import {test} from 'node:test';
import assert from 'node:assert/strict';
import {applicationJob} from './resumeApplication.mjs';

test('supports dataset and live links without dropping match information', () => {
  const result=applicationJob({url:'https://example.com/apply',match_percentage:80,title:'Analyst'});
  assert.equal(result.apply_url,'https://example.com/apply');
  assert.equal(result.match_percentage,80);
  assert.equal(applicationJob({apply_url:'https://example.com/direct'}).apply_url,'https://example.com/direct');
});
test('rejects missing, unsafe and credential-bearing links', () => {
  for(const apply_url of ['',null,'javascript:alert(1)','https://user:secret@example.com/']) {
    assert.equal(applicationJob({apply_url}),null);
  }
  assert.equal(applicationJob({apply_url:'bad',url:'https://example.com/apply'}).apply_url,'https://example.com/apply');
});
