module.exports.run = async (page, base, shot) => {
  const out = [];
  await page.waitForSelector('.mcard', {timeout: 8000});
  const cards = await page.$$eval('.mcard', r => r.length);
  out.push(['rate grid cards: ' + cards, cards >= 20]);
  // rate 5 movies 5 stars
  for (let i = 0; i < 5; i++) {
    await page.evaluate(idx => {
      const st = document.querySelectorAll('.mcard .stars')[idx];
      st.querySelectorAll('.star')[4].click();
    }, i);
    await new Promise(r=>setTimeout(r,150));
  }
  // recs tab
  await page.click('.tab[data-t="recs"]');
  await page.waitForSelector('.why', {timeout: 5000});
  const why = await page.$eval('.why', e => e.textContent);
  out.push(['explanation: ' + why.slice(0,60), /Because you liked/.test(why)]);
  const nRec = await page.$$eval('.mcard', r => r.length);
  out.push(['18 recs', nRec === 18]);
  // taste tab
  await page.click('.tab[data-t="taste"]');
  await page.waitForSelector('.taste-tag, .empty', {timeout: 5000});
  const taste = await page.$eval('.sect', e => e.textContent);
  out.push(['taste header: ' + taste, /5 rated/.test(taste)]);
  if (shot) await page.screenshot({path: shot});
  return out;
};
